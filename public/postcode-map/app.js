(() => {
  "use strict";

  const POSTCODE_URL = "/api/postcodes";
  const SWEDEN_CENTER = [62.0, 15.0];

  const els = {
    modeImport: document.getElementById("modeImport"),
    modeDraw: document.getElementById("modeDraw"),
    importPanel: document.getElementById("importPanel"),
    drawPanel: document.getElementById("drawPanel"),
    postcodeInput: document.getElementById("postcodeInput"),
    csvFile: document.getElementById("csvFile"),
    clusterDistance: document.getElementById("clusterDistance"),
    minimumRadius: document.getElementById("minimumRadius"),
    buildCircles: document.getElementById("buildCircles"),
    clearImport: document.getElementById("clearImport"),
    startCircle: document.getElementById("startCircle"),
    clearCircles: document.getElementById("clearCircles"),
    resultCount: document.getElementById("resultCount"),
    circleCount: document.getElementById("circleCount"),
    matchedCount: document.getElementById("matchedCount"),
    missingCount: document.getElementById("missingCount"),
    circleList: document.getElementById("circleList"),
    postcodeList: document.getElementById("postcodeList"),
    copyPostcodes: document.getElementById("copyPostcodes"),
    exportCsv: document.getElementById("exportCsv"),
    exportGeojson: document.getElementById("exportGeojson"),
    status: document.getElementById("status")
  };

  const state = {
    mode: "import",
    postcodes: [],
    postcodeByCode: new Map(),
    importedCodes: [],
    missingCodes: [],
    matchedCodes: [],
    circles: [],
    nextCircleId: 1
  };

  const map = L.map("map", { zoomControl: true }).setView(SWEDEN_CENTER, 5);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap contributors"
  }).addTo(map);

  const importedLayer = L.layerGroup().addTo(map);
  const matchedLayer = L.layerGroup().addTo(map);
  const circleLayer = L.featureGroup().addTo(map);

  const geomanAvailable = Boolean(map.pm);
  if (geomanAvailable) {
    map.pm.addControls({
      position: "topleft",
      drawMarker: false,
      drawPolyline: false,
      drawRectangle: false,
      drawPolygon: false,
      drawText: false,
      drawCircleMarker: false,
      cutPolygon: false,
      rotateMode: false,
      dragMode: false,
      editMode: true,
      removalMode: true,
      drawCircle: true
    });
    map.pm.setGlobalOptions({ snappable: false, continueDrawing: false });
  }

  function normalizePostcode(value) {
    const digits = String(value ?? "").replace(/\D/g, "");
    return /^\d{5}$/.test(digits) ? digits : null;
  }

  function formatPostcode(value) {
    const code = normalizePostcode(value);
    return code ? `${code.slice(0, 3)} ${code.slice(3)}` : String(value ?? "");
  }

  function parsePostcodes(text) {
    const matches = String(text ?? "").match(/(?<!\d)\d{3}\s?\d{2}(?!\d)/g) || [];
    return [...new Set(matches.map(normalizePostcode).filter(Boolean))];
  }

  function haversineMeters(a, b) {
    const R = 6371000;
    const toRad = deg => deg * Math.PI / 180;
    const dLat = toRad(b.lat - a.lat);
    const dLng = toRad(b.lng - a.lng);
    const lat1 = toRad(a.lat);
    const lat2 = toRad(b.lat);
    const x = Math.sin(dLat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(x));
  }

  function setStatus(message, type = "") {
    els.status.className = `status ${type}`.trim();
    els.status.textContent = message;
  }

  function startFallbackCircleDrawing() {
    const container = map.getContainer();
    container.style.cursor = "crosshair";
    setStatus("Klicka på kartan för cirkelns centrum.", "ok");

    map.once("click", firstEvent => {
      const center = firstEvent.latlng;
      const preview = L.circle(center, {
        radius: 100,
        color: "#155eef",
        fillColor: "#155eef",
        fillOpacity: 0.09,
        weight: 2.5
      }).addTo(circleLayer);

      const onMove = moveEvent => {
        preview.setRadius(Math.max(50, map.distance(center, moveEvent.latlng)));
      };

      const onFinish = finishEvent => {
        preview.setRadius(Math.max(50, map.distance(center, finishEvent.latlng)));
        map.off("mousemove", onMove);
        container.style.cursor = "";
        registerCircle(preview, { source: "drawn" });
        updateResults();
        setStatus("Cirkel skapad. Rita fler eller exportera postnumren.", "ok");
      };

      map.on("mousemove", onMove);
      setTimeout(() => map.once("click", onFinish), 0);
      setStatus("Flytta musen för radie och klicka igen för att avsluta cirkeln.", "ok");
    });
  }

  function switchMode(mode) {
    state.mode = mode;
    const importing = mode === "import";
    els.modeImport.classList.toggle("active", importing);
    els.modeDraw.classList.toggle("active", !importing);
    els.importPanel.classList.toggle("hidden", !importing);
    els.drawPanel.classList.toggle("hidden", importing);
    if (!importing) setStatus("Rita en eller flera cirklar på kartan. Postnummerresultatet uppdateras direkt.", "ok");
  }

  function averageCenter(points) {
    return {
      lat: points.reduce((sum, p) => sum + p.lat, 0) / points.length,
      lng: points.reduce((sum, p) => sum + p.lng, 0) / points.length
    };
  }

  function clusterPoints(points, thresholdMeters) {
    if (!points.length) return [];
    const parent = points.map((_, i) => i);
    const find = i => parent[i] === i ? i : (parent[i] = find(parent[i]));
    const union = (a, b) => {
      const ra = find(a), rb = find(b);
      if (ra !== rb) parent[rb] = ra;
    };

    for (let i = 0; i < points.length; i += 1) {
      for (let j = i + 1; j < points.length; j += 1) {
        if (haversineMeters(points[i], points[j]) <= thresholdMeters) union(i, j);
      }
    }

    const groups = new Map();
    points.forEach((point, index) => {
      const root = find(index);
      if (!groups.has(root)) groups.set(root, []);
      groups.get(root).push(point);
    });
    return [...groups.values()];
  }

  function clearCircleLayers() {
    state.circles.forEach(item => {
      if (circleLayer.hasLayer(item.layer)) circleLayer.removeLayer(item.layer);
    });
    state.circles = [];
    updateResults();
  }

  function circleName(index) {
    return `Område ${index}`;
  }

  function registerCircle(layer, options = {}) {
    const id = state.nextCircleId++;
    const item = {
      id,
      name: options.name || circleName(state.circles.length + 1),
      layer,
      source: options.source || "drawn"
    };
    state.circles.push(item);
    circleLayer.addLayer(layer);

    layer.on("pm:edit", updateResults);
    layer.on("pm:dragend", updateResults);
    layer.on("remove", () => {
      state.circles = state.circles.filter(c => c.layer !== layer);
      updateResults();
    });
    layer.on("click", () => {
      const center = layer.getLatLng();
      layer.bindPopup(`<strong>${item.name}</strong><br>${Math.round(layer.getRadius()).toLocaleString("sv-SE")} m radie`).openPopup();
      map.panTo(center);
    });
    return item;
  }

  function createAutoCircle(points, minRadius, index) {
    const center = averageCenter(points);
    const farthest = Math.max(...points.map(p => haversineMeters(center, p)), 0);
    const radius = Math.max(minRadius, farthest + 300);
    const layer = L.circle([center.lat, center.lng], {
      radius,
      color: "#155eef",
      fillColor: "#155eef",
      fillOpacity: 0.09,
      weight: 2.5
    });
    registerCircle(layer, { name: `Automatiskt område ${index + 1}`, source: "import" });
    if (layer.pm) layer.pm.enable({ allowSelfIntersection: false });
  }

  function renderImportedMarkers(points) {
    importedLayer.clearLayers();
    points.forEach(point => {
      L.circleMarker([point.lat, point.lng], {
        radius: 4.5,
        color: "#e06c1b",
        fillColor: "#e06c1b",
        fillOpacity: 0.85,
        weight: 1.4
      }).bindTooltip(formatPostcode(point.code)).addTo(importedLayer);
    });
  }

  function pointInsideAnyCircle(point) {
    return state.circles.some(item => {
      const center = item.layer.getLatLng();
      return haversineMeters({ lat: center.lat, lng: center.lng }, point) <= item.layer.getRadius();
    });
  }

  function getMatchedRecords() {
    if (!state.circles.length) return [];
    return state.postcodes.filter(pointInsideAnyCircle);
  }

  function renderMatchedMarkers(records) {
    matchedLayer.clearLayers();
    const imported = new Set(state.importedCodes);
    records.forEach(point => {
      L.circleMarker([point.lat, point.lng], {
        radius: imported.has(point.code) ? 5.2 : 3.5,
        color: "#147d64",
        fillColor: "#147d64",
        fillOpacity: imported.has(point.code) ? 0.9 : 0.55,
        weight: 1.2
      }).bindTooltip(`${formatPostcode(point.code)}${point.city ? ` · ${point.city}` : ""}`).addTo(matchedLayer);
    });
  }

  function countRecordsForCircle(item) {
    const center = item.layer.getLatLng();
    const radius = item.layer.getRadius();
    return state.postcodes.filter(point => haversineMeters({ lat: center.lat, lng: center.lng }, point) <= radius).length;
  }

  function updateCircleList() {
    els.circleList.innerHTML = "";
    state.circles.forEach((item, index) => {
      const center = item.layer.getLatLng();
      const count = countRecordsForCircle(item);
      const row = document.createElement("div");
      row.className = "circleItem";
      row.innerHTML = `
        <div>
          <strong>${item.name}</strong>
          <span>${(item.layer.getRadius() / 1000).toFixed(1).replace(".", ",")} km · ${count} postnummer</span>
        </div>
        <button type="button" aria-label="Ta bort ${item.name}">Ta bort</button>
      `;
      row.querySelector("div").addEventListener("click", () => {
        map.setView(center, Math.max(map.getZoom(), 11));
        item.layer.openPopup();
      });
      row.querySelector("button").addEventListener("click", () => {
        circleLayer.removeLayer(item.layer);
        state.circles = state.circles.filter(c => c !== item);
        updateResults();
      });
      els.circleList.appendChild(row);
    });
  }

  function updatePostcodeList(records) {
    const sorted = [...records].sort((a, b) => a.code.localeCompare(b.code, "sv"));
    state.matchedCodes = sorted.map(r => r.code);
    if (!sorted.length) {
      els.postcodeList.className = "postcodeList empty";
      els.postcodeList.textContent = "Inga postnummer valda ännu.";
      return;
    }
    els.postcodeList.className = "postcodeList";
    els.postcodeList.innerHTML = sorted.map(r => `<span class="postcodeChip">${formatPostcode(r.code)}</span>`).join("");
  }

  function updateResults() {
    const records = getMatchedRecords();
    renderMatchedMarkers(records);
    updateCircleList();
    updatePostcodeList(records);
    els.circleCount.textContent = String(state.circles.length);
    els.matchedCount.textContent = String(records.length);
    els.missingCount.textContent = String(state.missingCodes.length);
    els.resultCount.textContent = `${records.length} postnummer`;
  }

  function zoomToLayers() {
    const latlngs = [];
    importedLayer.eachLayer(layer => layer.getLatLng && latlngs.push(layer.getLatLng()));
    state.circles.forEach(item => {
      const bounds = item.layer.getBounds();
      latlngs.push(bounds.getNorthEast(), bounds.getSouthWest());
    });
    if (latlngs.length) map.fitBounds(L.latLngBounds(latlngs), { padding: [35, 35], maxZoom: 13 });
  }

  function buildFromImportedCodes() {
    if (!state.postcodes.length) {
      setStatus("Postnummerunderlaget är inte färdigladdat ännu.", "error");
      return;
    }
    const codes = parsePostcodes(els.postcodeInput.value);
    if (!codes.length) {
      setStatus("Lägg in minst ett femsiffrigt svenskt postnummer.", "error");
      return;
    }

    const found = [];
    const missing = [];
    codes.forEach(code => {
      const record = state.postcodeByCode.get(code);
      if (record) found.push(record);
      else missing.push(code);
    });
    state.importedCodes = found.map(r => r.code);
    state.missingCodes = missing;
    renderImportedMarkers(found);
    clearCircleLayers();

    if (!found.length) {
      setStatus(`Inga av ${codes.length} postnummer kunde matchas.`, "error");
      updateResults();
      return;
    }

    const threshold = Number(els.clusterDistance.value);
    const minRadius = Number(els.minimumRadius.value);
    const groups = clusterPoints(found, threshold);
    groups.forEach((group, index) => createAutoCircle(group, minRadius, index));
    updateResults();
    zoomToLayers();
    setStatus(`${found.length} av ${codes.length} postnummer matchade och grupperades i ${groups.length} cirklar.${missing.length ? ` ${missing.length} saknas i underlaget.` : ""}`, "ok");
  }

  async function readFile(file) {
    if (!file) return;
    const text = await file.text();
    const codes = parsePostcodes(text);
    els.postcodeInput.value = codes.map(formatPostcode).join("\n");
    setStatus(`${codes.length} unika postnummer hittades i ${file.name}.`, "ok");
  }

  function download(filename, content, type) {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  function exportCsv() {
    const records = getMatchedRecords().sort((a, b) => a.code.localeCompare(b.code, "sv"));
    const lines = [["postcode", "city", "latitude", "longitude"].join(",")];
    records.forEach(r => {
      const values = [formatPostcode(r.code), r.city || "", r.lat, r.lng];
      lines.push(values.map(v => `"${String(v).replaceAll('"', '""')}"`).join(","));
    });
    download("postnummer-urval.csv", `\uFEFF${lines.join("\n")}`, "text/csv;charset=utf-8");
  }

  function exportGeojson() {
    const features = state.circles.map((item, index) => {
      const center = item.layer.getLatLng();
      return {
        type: "Feature",
        properties: {
          name: item.name || circleName(index + 1),
          radiusMeters: Math.round(item.layer.getRadius()),
          source: item.source
        },
        geometry: { type: "Point", coordinates: [center.lng, center.lat] }
      };
    });
    download("omradescirklar.geojson", JSON.stringify({ type: "FeatureCollection", features }, null, 2), "application/geo+json;charset=utf-8");
  }

  async function copyPostcodes() {
    const text = state.matchedCodes.map(formatPostcode).join("\n");
    if (!text) {
      setStatus("Det finns inga postnummer att kopiera ännu.", "error");
      return;
    }
    await navigator.clipboard.writeText(text);
    setStatus(`${state.matchedCodes.length} postnummer kopierade.`, "ok");
  }

  map.on("pm:create", event => {
    if (event.shape !== "Circle") return;
    const layer = event.layer;
    layer.setStyle({ color: "#155eef", fillColor: "#155eef", fillOpacity: 0.09, weight: 2.5 });
    registerCircle(layer, { source: "drawn" });
    updateResults();
    setStatus("Cirkel skapad. Dra eller ändra radien för att uppdatera urvalet.", "ok");
  });

  map.on("pm:remove", event => {
    state.circles = state.circles.filter(item => item.layer !== event.layer);
    updateResults();
  });

  els.modeImport.addEventListener("click", () => switchMode("import"));
  els.modeDraw.addEventListener("click", () => switchMode("draw"));
  els.buildCircles.addEventListener("click", buildFromImportedCodes);
  els.csvFile.addEventListener("change", () => readFile(els.csvFile.files?.[0]));
  els.clearImport.addEventListener("click", () => {
    els.postcodeInput.value = "";
    els.csvFile.value = "";
    state.importedCodes = [];
    state.missingCodes = [];
    importedLayer.clearLayers();
    clearCircleLayers();
    setStatus("Importen är rensad.");
  });
  els.startCircle.addEventListener("click", () => {
    if (map.pm) map.pm.enableDraw("Circle");
    else startFallbackCircleDrawing();
  });
  els.clearCircles.addEventListener("click", () => {
    clearCircleLayers();
    setStatus("Alla cirklar är borttagna.");
  });
  els.copyPostcodes.addEventListener("click", copyPostcodes);
  els.exportCsv.addEventListener("click", exportCsv);
  els.exportGeojson.addEventListener("click", exportGeojson);

  fetch(POSTCODE_URL)
    .then(response => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.json();
    })
    .then(rows => {
      if (!Array.isArray(rows)) throw new Error(rows?.error || "Invalid postcode response.");
      const seen = new Set();
      state.postcodes = rows.flatMap(row => {
        const code = normalizePostcode(row.zipcode);
        const lat = Number(row.lat);
        const lng = Number(row.lng);
        if (!code || seen.has(code) || !Number.isFinite(lat) || !Number.isFinite(lng)) return [];
        seen.add(code);
        return [{ code, lat, lng, city: row.city || row.place || "" }];
      });
      state.postcodeByCode = new Map(state.postcodes.map(record => [record.code, record]));
      setStatus(`${state.postcodes.length.toLocaleString("sv-SE")} svenska postnummer är laddade via Cloudflare. Verktyget är klart.`, "ok");
    })
    .catch(error => {
      console.error(error);
      setStatus(`Postnummerunderlaget kunde inte laddas (${error.message}). Ladda om sidan eller kontrollera /api/postcodes.`, "error");
    });
})();
