const form = document.querySelector("#exportForm");
const result = document.querySelector("#result");

const chainInput = document.querySelector("#chain");
const countryInput = document.querySelector("#country");
const categoryInput = document.querySelector("#category");
const subtypeInput = document.querySelector("#subtype");
const formatInput = document.querySelector("#format");
const sourceInput = document.querySelector("#source");
const statusChip = document.querySelector("#statusChip");
const chainSuggestionsList = document.querySelector("#chainSuggestions");

const chainGroup = document.querySelector("#chainGroup");
const subtypeGroup = document.querySelector("#subtypeGroup");

let pollTimer = null;

const chainSuggestions = [
  { name: "7-Eleven", aliases: ["7 eleven", "seven eleven"], category: "retail_grocery", subtype: "auto" },
  { name: "Albert Heijn", aliases: ["ah"], category: "retail_grocery", subtype: "auto" },
  { name: "Aldi", aliases: [], category: "retail_grocery", subtype: "auto" },
  { name: "Apoteket", aliases: [], category: "healthcare_pharmacy", subtype: "auto" },
  { name: "Basic-Fit", aliases: ["basic fit"], category: "fitness_entertainment", subtype: "auto" },
  { name: "Best Western", aliases: [], category: "hotels", subtype: "auto" },
  { name: "Boots", aliases: [], category: "healthcare_pharmacy", subtype: "auto" },
  { name: "BP", aliases: [], category: "mobility_fuel", subtype: "auto" },
  { name: "Burger King", aliases: [], category: "food_restaurants", subtype: "auto" },
  { name: "Carrefour", aliases: ["carrefour market", "carrefour express"], category: "retail_grocery", subtype: "auto" },
  { name: "Circle K", aliases: [], category: "mobility_fuel", subtype: "auto" },
  { name: "Coop", aliases: ["coop supermarket"], category: "retail_grocery", subtype: "auto" },
  { name: "Costa Coffee", aliases: [], category: "food_restaurants", subtype: "auto" },
  { name: "DHL", aliases: [], category: "services", subtype: "auto" },
  { name: "Domino's", aliases: ["dominos", "domino's pizza"], category: "food_restaurants", subtype: "auto" },
  { name: "Elgiganten", aliases: [], category: "retail_grocery", subtype: "auto" },
  { name: "Esso", aliases: [], category: "mobility_fuel", subtype: "auto" },
  { name: "Espresso House", aliases: [], category: "food_restaurants", subtype: "auto" },
  { name: "FedEx", aliases: [], category: "services", subtype: "auto" },
  { name: "Fitness24Seven", aliases: ["fitness 24 seven"], category: "fitness_entertainment", subtype: "auto" },
  { name: "H&M", aliases: ["hm", "hennes & mauritz"], category: "retail_grocery", subtype: "auto" },
  { name: "Handelsbanken", aliases: [], category: "services", subtype: "auto" },
  { name: "Hilton", aliases: [], category: "hotels", subtype: "auto" },
  { name: "ICA", aliases: [], category: "retail_grocery", subtype: "auto" },
  { name: "IKEA", aliases: [], category: "retail_grocery", subtype: "auto" },
  { name: "Instabox", aliases: [], category: "services", subtype: "auto" },
  { name: "Joe & The Juice", aliases: ["joe and the juice"], category: "food_restaurants", subtype: "auto" },
  { name: "KFC", aliases: [], category: "food_restaurants", subtype: "auto" },
  { name: "Kiwi", aliases: [], category: "retail_grocery", subtype: "auto" },
  { name: "Lidl", aliases: [], category: "retail_grocery", subtype: "auto" },
  { name: "LloydsApotek", aliases: ["lloyds apotek"], category: "healthcare_pharmacy", subtype: "auto" },
  { name: "Marriott", aliases: [], category: "hotels", subtype: "auto" },
  { name: "MAX", aliases: ["max hamburgare", "max burgers"], category: "food_restaurants", subtype: "auto" },
  { name: "McDonald's", aliases: ["mcdonalds", "mcdonald’s"], category: "food_restaurants", subtype: "auto" },
  { name: "MediaMarkt", aliases: ["media markt"], category: "retail_grocery", subtype: "auto" },
  { name: "Netto", aliases: [], category: "retail_grocery", subtype: "auto" },
  { name: "Nordea", aliases: [], category: "services", subtype: "auto" },
  { name: "Nordic Wellness", aliases: [], category: "fitness_entertainment", subtype: "auto" },
  { name: "OKQ8", aliases: [], category: "mobility_fuel", subtype: "auto" },
  { name: "Pizza Hut", aliases: [], category: "food_restaurants", subtype: "auto" },
  { name: "PostNord", aliases: [], category: "services", subtype: "auto" },
  { name: "Preem", aliases: [], category: "mobility_fuel", subtype: "auto" },
  { name: "Radisson", aliases: [], category: "hotels", subtype: "auto" },
  { name: "REMA 1000", aliases: ["rema"], category: "retail_grocery", subtype: "auto" },
  { name: "SATS", aliases: [], category: "fitness_entertainment", subtype: "auto" },
  { name: "Scandic", aliases: [], category: "hotels", subtype: "auto" },
  { name: "SEB", aliases: [], category: "services", subtype: "auto" },
  { name: "Shell", aliases: [], category: "mobility_fuel", subtype: "auto" },
  { name: "SPAR", aliases: ["spar"], category: "retail_grocery", subtype: "auto" },
  { name: "Starbucks", aliases: [], category: "food_restaurants", subtype: "auto" },
  { name: "Subway", aliases: [], category: "food_restaurants", subtype: "auto" },
  { name: "Swedbank", aliases: [], category: "services", subtype: "auto" },
  { name: "Taco Bell", aliases: [], category: "food_restaurants", subtype: "auto" },
  { name: "Tesco", aliases: [], category: "retail_grocery", subtype: "auto" },
  { name: "UPS", aliases: [], category: "services", subtype: "auto" },
  { name: "Walgreens", aliases: [], category: "healthcare_pharmacy", subtype: "auto" },
  { name: "Zara", aliases: [], category: "retail_grocery", subtype: "auto" }
];

const subtypeOptions = {
  all: [
    ["auto", "Smart match — recommended"],
    ["all", "All B2C locations"]
  ],

  retail_grocery: [
    ["auto", "Smart match — recommended"],
    ["all", "All retail & grocery"],
    ["supermarket", "Supermarkets"],
    ["convenience", "Convenience stores"],
    ["fashion", "Fashion & clothing"],
    ["electronics", "Electronics"],
    ["furniture", "Furniture & home"],
    ["general_shop", "General shops"]
  ],

  food_restaurants: [
    ["auto", "Smart match — recommended"],
    ["all", "All food & restaurants"],
    ["fast_food", "Fast food"],
    ["restaurant", "Restaurants"],
    ["cafe", "Cafés"],
    ["bar_pub", "Bars & pubs"],
    ["food_court", "Food courts"],
    ["ice_cream", "Ice cream"]
  ],

  mobility_fuel: [
    ["auto", "Smart match — recommended"],
    ["all", "All mobility & fuel"],
    ["fuel", "Fuel stations"],
    ["charging", "EV charging stations"],
    ["car_rental", "Car rental"],
    ["car_service", "Car sales & repair"],
    ["bike_rental", "Bike rental"]
  ],

  hotels: [
    ["auto", "Smart match — recommended"],
    ["all", "All accommodation"],
    ["hotel", "Hotels"],
    ["motel", "Motels"],
    ["hostel", "Hostels"],
    ["guest_house", "Guest houses"]
  ],

  services: [
    ["auto", "Smart match — recommended"],
    ["all", "All services"],
    ["bank", "Banks & ATMs"],
    ["post_parcel", "Post offices & parcel lockers"],
    ["beauty", "Beauty, hair & cosmetics"],
    ["optician", "Opticians"]
  ],

  healthcare_pharmacy: [
    ["auto", "Smart match — recommended"],
    ["all", "All healthcare & pharmacy"],
    ["pharmacy", "Pharmacies"],
    ["clinic", "Clinics"],
    ["dentist", "Dentists"],
    ["doctors", "Doctors"],
    ["veterinary", "Veterinary"]
  ],

  fitness_entertainment: [
    ["auto", "Smart match — recommended"],
    ["all", "All fitness & entertainment"],
    ["fitness", "Gyms & fitness centres"],
    ["sports", "Sports centres"],
    ["cinema", "Cinemas & theatres"],
    ["bowling", "Bowling"],
    ["arcade", "Arcades"]
  ]
};

const steps = [
  {
    title: "Request received",
    text: "Your export has been queued and is ready to run."
  },
  {
    title: "Finding locations",
    text: "We are searching for matching locations in the selected market and category."
  },
  {
    title: "Cleaning data",
    text: "We are removing duplicates and standardizing the output."
  },
  {
    title: "Building file",
    text: "We are preparing the CSV file for download."
  },
  {
    title: "Ready to download",
    text: "Your completed export is available."
  }
];

init();

function init() {
  populateChainSuggestions();
  populateSubtypeOptions();

  document.querySelectorAll('input[name="exportMode"]').forEach((radio) => {
    radio.addEventListener("change", updateModeUI);
  });

  categoryInput.addEventListener("change", () => {
    populateSubtypeOptions();
    updateModeUI();
  });

  chainInput.addEventListener("change", applyChainSuggestion);
  chainInput.addEventListener("blur", applyChainSuggestion);

  document.querySelectorAll(".example").forEach((button) => {
    button.addEventListener("click", () => {
      const mode = button.dataset.mode || "chain";

      setExportMode(mode);

      chainInput.value = button.dataset.chain || "";
      countryInput.value = button.dataset.country || "";

      if (button.dataset.category) {
        categoryInput.value = button.dataset.category;
      }

      populateSubtypeOptions();

      if (button.dataset.subtype && subtypeInput) {
        subtypeInput.value = button.dataset.subtype;
      }

      updateModeUI();
      countryInput.focus();
    });
  });

  updateModeUI();
}

function populateChainSuggestions() {
  if (!chainSuggestionsList) return;

  chainSuggestionsList.innerHTML = chainSuggestions
    .map((item) => `<option value="${escapeHtml(item.name)}"></option>`)
    .join("");
}

function applyChainSuggestion() {
  const value = normalizeText(chainInput.value);
  if (!value) return;

  const match = chainSuggestions.find((item) => {
    const names = [item.name, ...(item.aliases || [])];
    return names.some((name) => normalizeText(name) === value);
  });

  if (!match) return;

  setExportMode("chain");
  chainInput.value = match.name;
  categoryInput.value = match.category;

  populateSubtypeOptions();

  if (subtypeInput) {
    subtypeInput.value = match.subtype || "auto";
  }

  updateModeUI();
}

function getExportMode() {
  const checked = document.querySelector('input[name="exportMode"]:checked');
  return checked ? checked.value : "chain";
}

function setExportMode(mode) {
  const radio = document.querySelector(`input[name="exportMode"][value="${mode}"]`);
  if (radio) {
    radio.checked = true;
  }
}

function updateModeUI() {
  const mode = getExportMode();

  populateSubtypeOptions();

  if (mode === "category") {
    chainGroup.style.display = "none";
    chainInput.required = false;
    chainInput.value = "";
    subtypeGroup.style.display = "grid";

    if (subtypeInput.value === "auto") {
      subtypeInput.value = "all";
    }
  } else {
    chainGroup.style.display = "grid";
    chainInput.required = true;
    subtypeGroup.style.display = "grid";

    if (!subtypeInput.value) {
      subtypeInput.value = "auto";
    }
  }
}

function populateSubtypeOptions() {
  const mode = getExportMode();
  const category = categoryInput.value || "all";
  const options = subtypeOptions[category] || subtypeOptions.all;
  const currentValue = subtypeInput.value;

  const visibleOptions =
    mode === "category"
      ? options.filter(([value]) => value !== "auto")
      : options;

  subtypeInput.innerHTML = visibleOptions
    .map(([value, label]) => `<option value="${value}">${label}</option>`)
    .join("");

  if (visibleOptions.some(([value]) => value === currentValue)) {
    subtypeInput.value = currentValue;
  } else {
    subtypeInput.value = visibleOptions[0][0];
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const exportMode = getExportMode();
  const chain = chainInput.value.trim();
  const country = countryInput.value.trim();
  const category = categoryInput ? categoryInput.value : "all";
  const subtype = subtypeInput ? subtypeInput.value : "auto";
  const format = formatInput ? formatInput.value : "CSV";
  const source = sourceInput ? sourceInput.value : "OpenStreetMap";
  const submitButton = form.querySelector("button");

  if (!country) {
    showError("Please enter a country.");
    return;
  }

  if (exportMode === "chain" && !chain) {
    showError("Please enter a chain or brand.");
    return;
  }

  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }

  const exportTitle =
    exportMode === "chain"
      ? `${chain} locations in ${country}`
      : `${getSubtypeLabel(category, subtype)} in ${country}`;

  submitButton.disabled = true;
  setChip("Starting", "running");

  renderStatus({
    currentStep: 0,
    progress: 8,
    badge: "Starting",
    title: "Preparing your export",
    subtitle:
      exportMode === "chain"
        ? `${chain} locations in ${country} will be searched using the selected category filter.`
        : `All ${getSubtypeLabel(category, subtype).toLowerCase()} in ${country} will be exported.`,
    meta: buildMeta({ exportMode, chain, country, category, subtype })
  });

  try {
    const response = await fetch("/api/start", {
      method: "POST",
      headers: {
        "content-type": "application/json"
      },
      body: JSON.stringify({
        exportMode,
        chain,
        country,
        category,
        subtype,
        format,
        source
      })
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Could not start the export.");
    }

    renderStatus({
      currentStep: 1,
      progress: 28,
      badge: "Running",
      title: "Finding locations",
      subtitle:
        exportMode === "chain"
          ? `The export is running. We are searching for ${getCategoryLabel(category).toLowerCase()} matching ${chain} in ${country}.`
          : `The export is running. We are searching for ${getSubtypeLabel(category, subtype).toLowerCase()} in ${country}.`,
      actionsUrl: data.actionsUrl,
      meta: buildMeta({ exportMode, chain, country, category, subtype })
    });

    startPolling({
      fileName: data.fileName,
      actionsUrl: data.actionsUrl,
      exportMode,
      chain,
      country,
      category,
      subtype,
      exportTitle
    });
  } catch (error) {
    showError(error.message);
  } finally {
    submitButton.disabled = false;
  }
});

function startPolling({ fileName, actionsUrl, exportMode, chain, country, category, subtype, exportTitle }) {
  let attempts = 0;
  const maxAttempts = 150;

  pollTimer = setInterval(async () => {
    attempts += 1;

    const phase = getPhase(attempts);

    setChip(phase.badge, "running");

    renderStatus({
      currentStep: phase.step,
      progress: phase.progress,
      badge: phase.badge,
      title: phase.title,
      subtitle: phase.subtitle
        .replace("{exportTitle}", exportTitle)
        .replace("{chain}", chain || "selected category")
        .replace("{country}", country)
        .replace("{category}", getCategoryLabel(category).toLowerCase())
        .replace("{subtype}", getSubtypeLabel(category, subtype).toLowerCase()),
      actionsUrl,
      meta: buildMeta({ exportMode, chain, country, category, subtype })
    });

    try {
      const response = await fetch(`/api/status?file=${encodeURIComponent(fileName)}`);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Could not read export status.");
      }

      if (data.ready) {
        clearInterval(pollTimer);
        pollTimer = null;

        setChip("Ready", "ready");

        renderReady({
          fileName,
          downloadUrl: data.downloadUrl,
          size: data.size,
          actionsUrl,
          exportMode,
          chain,
          country,
          category,
          subtype
        });
      }

      if (attempts >= maxAttempts) {
        clearInterval(pollTimer);
        pollTimer = null;
        setChip("Still running", "slow");

        renderStatus({
          currentStep: 3,
          progress: 82,
          badge: "Still running",
          title: "The export is still running",
          subtitle: "Large exports can take longer than expected. You can keep this page open and check again shortly.",
          actionsUrl,
          meta: buildMeta({ exportMode, chain, country, category, subtype })
        });
      }
    } catch (error) {
      clearInterval(pollTimer);
      pollTimer = null;
      showError(error.message);
    }
  }, 7000);
}

function getPhase(attempts) {
  if (attempts <= 2) {
    return {
      step: 1,
      progress: 32,
      badge: "Finding",
      title: "Finding locations",
      subtitle: "We are searching for {exportTitle}."
    };
  }

  if (attempts <= 5) {
    return {
      step: 2,
      progress: 58,
      badge: "Cleaning",
      title: "Cleaning data",
      subtitle: "We are validating results, removing duplicates and preparing structured address data."
    };
  }

  return {
    step: 3,
    progress: 78,
    badge: "Building file",
    title: "Building CSV file",
    subtitle: "Your export is being finalized. The download button will appear here when it is ready."
  };
}

function renderStatus({ currentStep, progress, badge, title, subtitle, actionsUrl, meta = [] }) {
  result.className = "result";

  result.innerHTML = `
    <div class="statusPanel">
      <div class="statusTitle">
        <div>
          <h3>${escapeHtml(title)}</h3>
          <p>${escapeHtml(subtitle)}</p>
        </div>
        <div class="statusBadge">${escapeHtml(badge)}</div>
      </div>

      ${meta.length ? `
        <div class="exportMeta">
          ${meta.map((item) => `
            <div>
              <span>${escapeHtml(item.label)}</span>
              <strong>${escapeHtml(item.value)}</strong>
            </div>
          `).join("")}
        </div>
      ` : ""}

      <div class="progressTrack" aria-label="Export progress">
        <div class="progressBar" style="width: ${progress}%"></div>
      </div>

      <div class="statusSteps">
        ${steps.map((step, index) => {
          const state = index < currentStep ? "done" : index === currentStep ? "active" : "";
          const icon = index < currentStep ? "✓" : index + 1;

          return `
            <div class="statusStep ${state}">
              <div class="stepDot">${icon}</div>
              <div>
                <strong>${escapeHtml(step.title)}</strong>
                <span>${escapeHtml(step.text)}</span>
              </div>
            </div>
          `;
        }).join("")}
      </div>

      ${actionsUrl ? `
        <details class="technicalDetails">
          <summary>Technical details</summary>
          <a href="${actionsUrl}" target="_blank" rel="noreferrer">View background run</a>
        </details>
      ` : ""}
    </div>
  `;
}

function renderReady({ fileName, downloadUrl, size, actionsUrl, exportMode, chain, country, category, subtype }) {
  const sizeText = size ? `${Math.max(1, Math.round(size / 1024))} KB` : "CSV";

  result.className = "result";

  result.innerHTML = `
    <div class="readyBox">
      <div class="statusTitle">
        <div>
          <h3>Your export is ready</h3>
          <p>The CSV file has been created and is ready to download.</p>
        </div>
        <div class="statusBadge">Ready</div>
      </div>

      <div class="exportMeta">
        ${buildMeta({ exportMode, chain, country, category, subtype }).map((item) => `
          <div>
            <span>${escapeHtml(item.label)}</span>
            <strong>${escapeHtml(item.value)}</strong>
          </div>
        `).join("")}
      </div>

      <div class="progressTrack">
        <div class="progressBar" style="width: 100%"></div>
      </div>

      <div class="fileCard">
        <div>
          <span>Generated file</span>
          <strong>${escapeHtml(fileName)}</strong>
        </div>
        <div>
          <span>Size</span>
          <strong>${escapeHtml(sizeText)}</strong>
        </div>
      </div>

      <a class="downloadButton" href="${downloadUrl}">
        Download CSV
      </a>

      <p class="smallText">
        The CSV includes category, address fields, formatted address, coordinates and source identifiers.
      </p>

      ${actionsUrl ? `
        <details class="technicalDetails">
          <summary>Technical details</summary>
          <a href="${actionsUrl}" target="_blank" rel="noreferrer">View background run</a>
        </details>
      ` : ""}
    </div>
  `;
}

function buildMeta({ exportMode, chain, country, category, subtype }) {
  const meta = [
    { label: "Export type", value: exportMode === "chain" ? "Specific chain" : "Entire category" },
    { label: "Country", value: country },
    { label: "Category", value: getCategoryLabel(category) }
  ];

  if (exportMode === "chain") {
    meta.splice(1, 0, { label: "Chain", value: chain });
  } else {
    meta.splice(1, 0, { label: "Subtype", value: getSubtypeLabel(category, subtype) });
  }

  return meta;
}

function getCategoryLabel(value) {
  const labels = {
    all: "All B2C locations",
    retail_grocery: "Retail & grocery",
    food_restaurants: "Food & restaurants",
    mobility_fuel: "Mobility & fuel",
    hotels: "Hotels & accommodation",
    services: "Services",
    healthcare_pharmacy: "Healthcare & pharmacy",
    fitness_entertainment: "Fitness & entertainment"
  };

  return labels[value] || "All B2C locations";
}

function getSubtypeLabel(category, subtype) {
  const options = subtypeOptions[category] || subtypeOptions.all;
  const match = options.find(([value]) => value === subtype);
  return match ? match[1] : "Smart match — recommended";
}

function showError(message) {
  setChip("Error", "error");

  result.className = "result";
  result.innerHTML = `
    <div class="errorBox">
      <strong>Something went wrong</strong><br>
      ${escapeHtml(message)}
    </div>
  `;
}

function setChip(text, mode) {
  if (!statusChip) return;

  statusChip.textContent = text;
  statusChip.className = "cardBadge";

  if (mode === "ready") {
    statusChip.style.background = "#dcfae6";
    statusChip.style.color = "#079455";
  } else if (mode === "error") {
    statusChip.style.background = "#fff1f0";
    statusChip.style.color = "#912018";
  } else if (mode === "slow") {
    statusChip.style.background = "#fff7e6";
    statusChip.style.color = "#b54708";
  } else {
    statusChip.style.background = "#ecf7fb";
    statusChip.style.color = "#008ca0";
  }
}

function normalizeText(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .replace("’", "'")
    .replace(/\s+/g, " ");
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;"
  }[char]));
}
