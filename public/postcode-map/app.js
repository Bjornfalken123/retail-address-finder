(() => {
  "use strict";

  const POSTCODE_URL = "/data/postcodes-se.json";
  const SWEDEN_CENTER = [62.0, 15.0];

  const els = {
    modeImport: document.getElementById("modeImport"),
    modeDraw: document.getElementById("modeDraw"),
    importPanel: document.getElementById("importPanel"),
    importResults: document.getElementById("importResults"),
    drawPanel: document.getElementById("drawPanel"),
    drawResults: document.getElementById("drawResults"),
    postcodeInput: document.getElementById("postcodeInput"),
    csvFile: document.getElementById("csvFile"),
    showPostcodes: document.getElementById("showPostcodes"),
    clearImport: document.getElementById("clearImport"),
    zoomImported: document.getElementById("zoomImported"),
    importResultCount: document.getElementById("importResultCount"),
    inputCount: document.getElementById("inputCount"),
    placedCount: document.getElementById("placedCount"),
    approxCount: document.getElementById("approxCount"),
    importMissingCount: document.getElementById("importMissingCount"),
    importEmpty: document.getElementById("importEmpty"),
    importActions: document.getElementById("importActions"),
    importList: document.getElementById("importList"),
    startCircle: document.getElementById("startCircle"),
    clearCircles: document.getElementById("clearCircles"),
    drawEmpty: document.getElementById("drawEmpty"),
    drawResultContent: document.getElementById("drawResultContent"),
    resultCount: document.getElementById("resultCount"),
    circleCount: document.getElementById("circleCount"),
    matchedCount: document.getElementById("matchedCount"),
    excludedCount: document.getElementById("excludedCount"),
    circleList: document.getElementById("circleList"),
    postcodeList: document.getElementById("postcodeList"),
    copyPostcodes: document.getElementById("copyPostcodes"),
    exportCsv: document.getElementById("exportCsv"),
    exportGeojson: document.getElementById("exportGeojson"),
    dataDot: document.getElementById("dataDot"),
    dataState: document.getElementById("dataState"),
    dataMeta: document.getElementById("dataMeta"),
    status: document.getElementById("status"),
    mapLegend: document.getElementById("mapLegend")
  };

  const state = {
    mode: "import",
    postcodes: [],
    postcodeByCode: new Map(),
    importedRecords: [],
    importedCodes: [],
    missingCodes: [],
    matchedCodes: [],
    circles: [],
    nextCircleId: 1,
    dataReady: false,
    dataMeta: null,
    importMarkerByCode: new Map()
  };

  const map = L.map("map", { zoomControl: true }).setView(SWEDEN_CENTER, 5);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap contributors"
  }).addTo(map);

  const importedLayer = L.layerGroup().addTo(map);
  const matchedLayer = L.layerGroup();
  const circleLayer = L.featureGroup();
  const geomanAvailable = Boolean(map.pm);

  function normalizePostcode(value) {
    const digits = String(value ?? "").replace(/\D/g, "");
    return /^\d{5}$/.test(digits) ? digits : null;
  }

  function formatPostcode(value) {
    const code = normalizePostcode(value);
    return code ? `${code.slice(0, 3)} ${code.slice(3)}` : String(value ?? "");
  }

  function parsePostcodes(text) {
    const matches = String(text ?? "").match(/\b\d{3}\s?\d{2}\b/g) || [];
    return [...new Set(matches.map(normalizePostcode).filter(Boolean))];
  }

  function haversineMeters(a, b) {
    const R = 6371000;
    const toRad = deg => deg * Math.PI / 180;
    const dLat = toRad(b.lat - a.lat);
    const dLng = toRad(b.lng - a.lng);
    const lat1 = toRad(a.lat);
    const lat2 = toRad(b.lat);
    const x = Math.sin(dLat / 2) ** 2 +
      Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2;
    return 2 * R * Math.asin(Math.sqrt(x));
  }

  function setStatus(message = "", type = "") {
    els.status.className = `status statusText ${type}`.trim();
    els.status.textContent = message;
  }

  function setDataState(kind, title, meta) {
    els.dataDot.className = `dataDot ${kind}`;
    els.dataState.textContent = title;
    els.dataMeta.textContent = meta;
  }

  function setDataReady(ready) {
    state.dataReady = ready;
    els.showPostcodes.disabled = !ready;
    els.startCircle.disabled = !ready;
    els.modeDraw.disabled = !ready;
  }

  function showLayer(layer) {
    if (!map.hasLayer(layer)) layer.addTo(map);
  }

  function hideLayer(layer) {
    if (map.hasLayer(layer)) map.removeLayer(layer);
  }

  function configureDrawControls(active) {
    if (!geomanAvailable) return;

    if (!active) {
      try { map.pm.disableDraw(); } catch (_) {}
      try { map.pm.disableGlobalEditMode(); } catch (_) {}
      try { map.pm.disableGlobalRemovalMode(); } catch (_) {}
      try { map.pm.removeControls(); } catch (_) {}
      return;
    }

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

  function renderLegend() {
    if (state.mode === "import") {
      els.mapLegend.innerHTML = `
        <span><i class="legendDot precise"></i>Address-derived / higher confidence</span>
        <span><i class="legendDot approx"></i>Approximate fallback</span>
      `;
    } else {
      els.mapLegend.innerHTML = `
        <span><i class="legendRing"></i>Target circle</span>
        <span><i class="legendDot matched"></i>Matched postcode</span>
      `;
    }
  }

  function switchMode(mode) {
    state.mode = mode;
    const importing = mode === "import";

    els.modeImport.classList.toggle("active", importing);
    els.modeDraw.classList.toggle("active", !importing);
    els.modeImport.setAttribute("aria-selected", String(importing));
    els.modeDraw.setAttribute("aria-selected", String(!importing));

    els.importPanel.classList.toggle("hidden", !importing);
    els.importResults.classList.toggle("hidden", !importing);
    els.drawPanel.classList.toggle("hidden", importing);
    els.drawResults.classList.toggle("hidden", importing);

    if (importing) {
      showLayer(importedLayer);
      hideLayer(matchedLayer);
      hideLayer(circleLayer);
      configureDrawControls(false);
      setStatus(state.importedRecords.length ? "Imported postcodes are shown on the map." : "");
    } else {
      hideLayer(importedLayer);
      showLayer(circleLayer);
      showLayer(matchedLayer);
      configureDrawControls(true);
      updateDrawResults();
      setStatus("Draw or edit circles on the map. Results update automatically.");
    }

    renderLegend();
    setTimeout(() => map.invalidateSize(), 0);
  }

  function precisionInfo(point) {
    if (point.coordinateSource === "osm-address-centroid") {
      return {
        kind: "good",
        label: "Address-derived",
        detail: point.osmSampleCount > 1
          ? `${point.osmSampleCount} OSM address points`
          : "1 OSM address point"
      };
    }
    if (point.precision === "low") {
      return {
        kind: "low",
        label: "Approximate",
        detail: "Low-precision fallback"
      };
    }
    return {
      kind: "fallback",
      label: "Fallback",
      detail: "GeoNames position"
    };
  }

  function postcodePopup(point) {
    const quality = precisionInfo(point);
    const place = [point.city, point.municipality]
      .filter(Boolean)
      .filter((value, index, list) => list.indexOf(value) === index)
      .join(" · ");

    return `
      <div class="popupTitle">${formatPostcode(point.code)}</div>
      ${place ? `<div class="popupMeta">${place}</div>` : ""}
      <div class="popupQuality">${quality.label} · ${quality.detail}</div>
    `;
  }

  function renderImportedMarkers(records) {
    importedLayer.clearLayers();
    state.importMarkerByCode.clear();

    records.forEach(point => {
      const approximate = point.precision === "low";
      const marker = L.circleMarker([point.lat, point.lng], {
        radius: approximate ? 6 : 5,
        color: approximate ? "#dc6803" : "#175cd3",
        fillColor: approximate ? "#ffffff" : "#175cd3",
        fillOpacity: approximate ? 0.92 : 0.82,
        weight: approximate ? 2.2 : 1.4
      });
      marker.bindPopup(postcodePopup(point));
      marker.bindTooltip(formatPostcode(point.code), { direction: "top", offset: [0, -4] });
      marker.addTo(importedLayer);
      state.importMarkerByCode.set(point.code, marker);
    });
  }

  function renderImportList(records, missing) {
    const rows = [];

    [...records]
      .sort((a, b) => a.code.localeCompare(b.code, "sv"))
      .forEach(point => {
        const quality = precisionInfo(point);
        const place = point.city || point.municipality || "";
        rows.push(`
          <button class="qualityRow qualityRowButton" type="button" data-code="${point.code}">
            <span class="qualityCode">${formatPostcode(point.code)}</span>
            <span class="qualityPlace" title="${place}">${place || "—"}</span>
            <span class="qualityBadge ${quality.kind}">${quality.label}</span>
          </button>
        `);
      });

    [...missing]
      .sort((a, b) => a.localeCompare(b, "sv"))
      .forEach(code => {
        rows.push(`
          <div class="qualityRow">
            <span class="qualityCode">${formatPostcode(code)}</span>
            <span class="qualityPlace">No position</span>
            <span class="qualityBadge missing">Missing</span>
          </div>
        `);
      });

    els.importList.innerHTML = rows.join("");

    els.importList.querySelectorAll("[data-code]").forEach(row => {
      row.addEventListener("click", () => {
        const marker = state.importMarkerByCode.get(row.dataset.code);
        if (!marker) return;
        map.setView(marker.getLatLng(), Math.max(map.getZoom(), 14));
        marker.openPopup();
      });
    });
  }

  function updateImportResults(totalInput, records, missing) {
    const approximate = records.filter(point => point.precision === "low").length;

    els.inputCount.textContent = String(totalInput);
    els.placedCount.textContent = String(records.length);
    els.approxCount.textContent = String(approximate);
    els.importMissingCount.textContent = String(missing.length);
    els.importResultCount.textContent = `${records.length} shown`;
    els.zoomImported.disabled = records.length === 0;

    const hasInput = totalInput > 0;
    els.importEmpty.classList.toggle("hidden", hasInput);
    els.importActions.classList.toggle("hidden", !hasInput);
    renderImportList(records, missing);
  }

  function fitImported() {
    const latlngs = [];
    importedLayer.eachLayer(layer => {
      if (layer.getLatLng) latlngs.push(layer.getLatLng());
    });
    if (!latlngs.length) return;

    if (latlngs.length === 1) {
      map.setView(latlngs[0], 14);
      return;
    }

    map.fitBounds(L.latLngBounds(latlngs), {
      padding: [42, 42],
      maxZoom: 14
    });
  }

  function showImportedPostcodes() {
    if (!state.dataReady) {
      setStatus("Postcode data is still loading.", "error");
      return;
    }

    const codes = parsePostcodes(els.postcodeInput.value);
    if (!codes.length) {
      setStatus("Enter at least one five-digit Swedish postcode.", "error");
      return;
    }

    const records = [];
    const missing = [];

    codes.forEach(code => {
      const point = state.postcodeByCode.get(code);
      if (point) records.push(point);
      else missing.push(code);
    });

    state.importedRecords = records;
    state.importedCodes = records.map(point => point.code);
    state.missingCodes = missing;

    renderImportedMarkers(records);
    updateImportResults(codes.length, records, missing);
    fitImported();

    const approximate = records.filter(point => point.precision === "low").length;

    if (!records.length) {
      setStatus("None of the postcodes could be mapped with the current dataset.", "error");
      return;
    }

    const messages = [`${records.length} of ${codes.length} postcodes are shown on the map.`];
    if (approximate) messages.push(`${approximate} use approximate positions.`);
    if (missing.length) messages.push(`${missing.length} are missing from the dataset.`);

    setStatus(messages.join(" "), approximate || missing.length ? "" : "ok");
  }

  function clearImport() {
    els.postcodeInput.value = "";
    els.csvFile.value = "";
    state.importedRecords = [];
    state.importedCodes = [];
    state.missingCodes = [];
    importedLayer.clearLayers();
    updateImportResults(0, [], []);
    setStatus("The postcode list has been cleared.");
  }

  function pointInsideCircle(point, item) {
    const center = item.layer.getLatLng();
    return haversineMeters(
      { lat: center.lat, lng: center.lng },
      point
    ) <= item.layer.getRadius();
  }

  function pointInsideAnyCircle(point) {
    return state.circles.some(item => pointInsideCircle(point, item));
  }

  function getMatchedRecords() {
    if (!state.circles.length) return [];
    return state.postcodes.filter(
      point => point.precision !== "low" && pointInsideAnyCircle(point)
    );
  }

  function getExcludedLowPrecisionRecords() {
    if (!state.circles.length) return [];
    return state.postcodes.filter(
      point => point.precision === "low" && pointInsideAnyCircle(point)
    );
  }

  function renderMatchedMarkers(records) {
    matchedLayer.clearLayers();

    records.forEach(point => {
      L.circleMarker([point.lat, point.lng], {
        radius: 4.2,
        color: "#067647",
        fillColor: "#067647",
        fillOpacity: 0.78,
        weight: 1.2
      })
        .bindPopup(postcodePopup(point))
        .bindTooltip(formatPostcode(point.code), { direction: "top", offset: [0, -3] })
        .addTo(matchedLayer);
    });
  }

  function circleName(index) {
    return `Area ${index}`;
  }

  function registerCircle(layer, options = {}) {
    const item = {
      id: state.nextCircleId++,
      name: options.name || circleName(state.circles.length + 1),
      layer
    };

    state.circles.push(item);
    if (!circleLayer.hasLayer(layer)) circleLayer.addLayer(layer);

    layer.on("pm:edit", updateDrawResults);
    layer.on("pm:dragend", updateDrawResults);
    layer.on("click", () => {
      const count = state.postcodes.filter(
        point => point.precision !== "low" && pointInsideCircle(point, item)
      ).length;
      layer
        .bindPopup(`
          <div class="popupTitle">${item.name}</div>
          <div class="popupMeta">${(layer.getRadius() / 1000).toFixed(1)} km radius · ${count} postcodes</div>
        `)
        .openPopup();
    });

    return item;
  }

  function removeCircle(item) {
    circleLayer.removeLayer(item.layer);
    state.circles = state.circles.filter(circle => circle !== item);
    updateDrawResults();
  }

  function clearCircles() {
    circleLayer.clearLayers();
    state.circles = [];
    matchedLayer.clearLayers();
    updateDrawResults();
    setStatus("All circles have been removed.");
  }

  function updateCircleList() {
    els.circleList.innerHTML = "";

    state.circles.forEach(item => {
      const matched = state.postcodes.filter(
        point => point.precision !== "low" && pointInsideCircle(point, item)
      ).length;
      const excluded = state.postcodes.filter(
        point => point.precision === "low" && pointInsideCircle(point, item)
      ).length;
      const center = item.layer.getLatLng();

      const row = document.createElement("div");
      row.className = "circleItem";
      row.innerHTML = `
        <div class="circleItemMain">
          <strong>${item.name}</strong>
          <span>${(item.layer.getRadius() / 1000).toFixed(1)} km · ${matched} postcodes${excluded ? ` · ${excluded} low-confidence excluded` : ""}</span>
        </div>
        <button type="button" aria-label="Remove ${item.name}">Remove</button>
      `;

      row.querySelector(".circleItemMain").addEventListener("click", () => {
        map.setView(center, Math.max(map.getZoom(), 11));
        item.layer.openPopup();
      });
      row.querySelector("button").addEventListener("click", () => removeCircle(item));
      els.circleList.appendChild(row);
    });
  }

  function updatePostcodeList(records) {
    const sorted = [...records].sort((a, b) => a.code.localeCompare(b.code, "sv"));
    state.matchedCodes = sorted.map(record => record.code);

    if (!sorted.length) {
      els.postcodeList.className = "postcodeList empty";
      els.postcodeList.textContent = "No postcodes matched yet.";
      return;
    }

    els.postcodeList.className = "postcodeList";
    els.postcodeList.innerHTML = sorted
      .map(record => `<span class="postcodeChip">${formatPostcode(record.code)}</span>`)
      .join("");
  }

  function updateDrawResults() {
    const matched = getMatchedRecords();
    const excluded = getExcludedLowPrecisionRecords();

    renderMatchedMarkers(matched);
    updateCircleList();
    updatePostcodeList(matched);

    els.circleCount.textContent = String(state.circles.length);
    els.matchedCount.textContent = String(matched.length);
    els.excludedCount.textContent = String(excluded.length);
    els.resultCount.textContent = `${matched.length} postcodes`;
    els.clearCircles.disabled = state.circles.length === 0;
    els.copyPostcodes.disabled = matched.length === 0;
    els.exportCsv.disabled = matched.length === 0;
    els.exportGeojson.disabled = state.circles.length === 0;

    const hasCircles = state.circles.length > 0;
    els.drawEmpty.classList.toggle("hidden", hasCircles);
    els.drawResultContent.classList.toggle("hidden", !hasCircles);
  }

  function startFallbackCircleDrawing() {
    const container = map.getContainer();
    container.style.cursor = "crosshair";
    setStatus("Click the map to set the circle centre.");

    map.once("click", firstEvent => {
      const center = firstEvent.latlng;
      const preview = L.circle(center, {
        radius: 100,
        color: "#175cd3",
        fillColor: "#175cd3",
        fillOpacity: 0.09,
        weight: 2.4
      }).addTo(circleLayer);

      const onMove = moveEvent => {
        preview.setRadius(Math.max(50, map.distance(center, moveEvent.latlng)));
      };

      const onFinish = finishEvent => {
        preview.setRadius(Math.max(50, map.distance(center, finishEvent.latlng)));
        map.off("mousemove", onMove);
        container.style.cursor = "";
        registerCircle(preview);
        updateDrawResults();
        setStatus("Circle created. The postcode result has been updated.", "ok");
      };

      map.on("mousemove", onMove);
      setTimeout(() => map.once("click", onFinish), 0);
      setStatus("Move the pointer to set the radius, then click again to finish.");
    });
  }

  async function readFile(file) {
    if (!file) return;
    try {
      const text = await file.text();
      const codes = parsePostcodes(text);
      els.postcodeInput.value = codes.map(formatPostcode).join("\n");
      if (!codes.length) {
        setStatus(`No five-digit Swedish postcodes were found in ${file.name}.`, "error");
        return;
      }
      setStatus(`${codes.length} unique postcodes found in ${file.name}. Choose “Show postcodes on map”.`, "ok");
    } catch (error) {
      console.error(error);
      setStatus("The file could not be read.", "error");
    }
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
    const records = getMatchedRecords()
      .sort((a, b) => a.code.localeCompare(b.code, "sv"));

    if (!records.length) {
      setStatus("There are no matched postcodes to export.", "error");
      return;
    }

    const header = [
      "postcode", "city", "municipality", "county",
      "latitude", "longitude", "coordinate_source", "precision"
    ];
    const lines = [header.join(",")];

    records.forEach(record => {
      const values = [
        formatPostcode(record.code),
        record.city || "",
        record.municipality || "",
        record.county || "",
        record.lat,
        record.lng,
        record.coordinateSource || "",
        record.precision || ""
      ];
      lines.push(values.map(value => `"${String(value).replaceAll('"', '""')}"`).join(","));
    });

    download("postcodes-in-circles.csv", `\uFEFF${lines.join("\n")}`, "text/csv;charset=utf-8");
    setStatus(`${records.length} postcodes exported to CSV.`, "ok");
  }

  function exportGeojson() {
    if (!state.circles.length) {
      setStatus("There are no circles to export.", "error");
      return;
    }

    const features = state.circles.map((item, index) => {
      const center = item.layer.getLatLng();
      return {
        type: "Feature",
        properties: {
          name: item.name || circleName(index + 1),
          radiusMeters: Math.round(item.layer.getRadius())
        },
        geometry: {
          type: "Point",
          coordinates: [center.lng, center.lat]
        }
      };
    });

    download(
      "target-circles.geojson",
      JSON.stringify({ type: "FeatureCollection", features }, null, 2),
      "application/geo+json;charset=utf-8"
    );
    setStatus(`${features.length} circles exported as GeoJSON.`, "ok");
  }

  async function copyPostcodes() {
    const text = state.matchedCodes.map(formatPostcode).join("\n");
    if (!text) {
      setStatus("There are no matched postcodes to copy.", "error");
      return;
    }

    try {
      await navigator.clipboard.writeText(text);
      setStatus(`${state.matchedCodes.length} postcodes copied.`, "ok");
    } catch (error) {
      console.error(error);
      setStatus("Could not copy automatically. Open the postcode list and copy it manually.", "error");
    }
  }

  map.on("pm:create", event => {
    if (state.mode !== "draw" || event.shape !== "Circle") return;

    const layer = event.layer;
    layer.setStyle({
      color: "#175cd3",
      fillColor: "#175cd3",
      fillOpacity: 0.09,
      weight: 2.4
    });
    registerCircle(layer);
    updateDrawResults();
    setStatus("Circle created. Drag it or change the radius to refine the selection.", "ok");
  });

  map.on("pm:remove", event => {
    state.circles = state.circles.filter(item => item.layer !== event.layer);
    updateDrawResults();
  });

  els.modeImport.addEventListener("click", () => switchMode("import"));
  els.modeDraw.addEventListener("click", () => {
    if (!state.dataReady) return;
    switchMode("draw");
  });
  els.showPostcodes.addEventListener("click", showImportedPostcodes);
  els.clearImport.addEventListener("click", clearImport);
  els.zoomImported.addEventListener("click", fitImported);
  els.csvFile.addEventListener("change", () => readFile(els.csvFile.files?.[0]));
  els.postcodeInput.addEventListener("keydown", event => {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter" && state.dataReady) {
      showImportedPostcodes();
    }
  });

  els.startCircle.addEventListener("click", () => {
    if (!state.dataReady) {
      setStatus("Postcode data must be loaded before you can create a selection.", "error");
      return;
    }
    if (geomanAvailable) {
      map.pm.enableDraw("Circle", {
        snappable: false,
        continueDrawing: false,
        pathOptions: {
          color: "#175cd3",
          fillColor: "#175cd3",
          fillOpacity: 0.09,
          weight: 2.4
        }
      });
    } else {
      startFallbackCircleDrawing();
    }
  });

  els.clearCircles.addEventListener("click", clearCircles);
  els.copyPostcodes.addEventListener("click", copyPostcodes);
  els.exportCsv.addEventListener("click", exportCsv);
  els.exportGeojson.addEventListener("click", exportGeojson);

  setDataReady(false);
  setDataState("loading", "Loading postcode data…", "Preparing map data");
  updateImportResults(0, [], []);
  updateDrawResults();
  renderLegend();
  configureDrawControls(false);

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 45000);

  fetch(POSTCODE_URL, { cache: "no-cache", signal: controller.signal })
    .then(response => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.json();
    })
    .then(payload => {
      const rows = payload?.postcodes;
      const meta = payload?.meta || {};

      if (!Array.isArray(rows)) throw new Error("postcode data is missing the postcodes array");
      if (rows.length < 5000) throw new Error(`unexpectedly small postcode dataset (${rows.length})`);

      const seen = new Set();
      state.postcodes = rows.flatMap(row => {
        const code = normalizePostcode(row.code);
        const lat = Number(row.lat);
        const lng = Number(row.lng);

        if (!code || seen.has(code) || !Number.isFinite(lat) || !Number.isFinite(lng)) {
          return [];
        }

        seen.add(code);
        return [{
          code,
          lat,
          lng,
          city: row.city || "",
          municipality: row.municipality || "",
          county: row.county || "",
          accuracy: Number(row.accuracy) || 0,
          sharedCoordinateCount: Number(row.sharedCoordinateCount) || 1,
          coordinateSource: row.coordinateSource || "geonames",
          osmSampleCount: Number(row.osmSampleCount) || 0,
          precision: row.precision || "fallback"
        }];
      });

      if (state.postcodes.length < 5000) {
        throw new Error(`only ${state.postcodes.length} valid postcodes remained after validation`);
      }

      state.postcodeByCode = new Map(
        state.postcodes.map(record => [record.code, record])
      );
      state.dataMeta = meta;
      setDataReady(true);

      const osmCount = state.postcodes.filter(
        point => point.coordinateSource === "osm-address-centroid"
      ).length;
      const lowCount = state.postcodes.filter(
        point => point.precision === "low"
      ).length;

      setDataState(
        "ready",
        "Postcode data is ready",
        `${state.postcodes.length.toLocaleString("en-GB")} postcodes · ${osmCount.toLocaleString("en-GB")} address-derived · ${lowCount.toLocaleString("en-GB")} low precision`
      );
    })
    .catch(error => {
      console.error(error);
      setDataReady(false);
      const reason = error?.name === "AbortError"
        ? "the request timed out"
        : error.message;
      setDataState("error", "Could not load postcode data", reason);
      setStatus("Reload the page. If the issue persists, the postcode dataset needs to be checked.", "error");
    })
    .finally(() => clearTimeout(timeoutId));
})();