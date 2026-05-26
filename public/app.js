const form = document.querySelector("#exportForm");
const result = document.querySelector("#result");
const chainInput = document.querySelector("#chain");
const countryInput = document.querySelector("#country");
const categoryInput = document.querySelector("#category");
const formatInput = document.querySelector("#format");
const sourceInput = document.querySelector("#source");
const statusChip = document.querySelector("#statusChip");

let pollTimer = null;

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

document.querySelectorAll(".example").forEach((button) => {
  button.addEventListener("click", () => {
    chainInput.value = button.dataset.chain;
    countryInput.value = button.dataset.country;

    if (categoryInput && button.dataset.category) {
      categoryInput.value = button.dataset.category;
    }

    chainInput.focus();
  });
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const chain = chainInput.value.trim();
  const country = countryInput.value.trim();
  const category = categoryInput ? categoryInput.value : "all";
  const format = formatInput ? formatInput.value : "CSV";
  const source = sourceInput ? sourceInput.value : "OpenStreetMap";
  const submitButton = form.querySelector("button");

  if (!chain || !country) {
    showError("Please enter both a chain and a country.");
    return;
  }

  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }

  submitButton.disabled = true;
  setChip("Starting", "running");

  renderStatus({
    currentStep: 0,
    progress: 8,
    badge: "Starting",
    title: "Preparing your export",
    subtitle: `${chain} locations in ${country} will be searched using the selected category filter.`,
    meta: [
      { label: "Chain", value: chain },
      { label: "Country", value: country },
      { label: "Category", value: getCategoryLabel(category) }
    ]
  });

  try {
    const response = await fetch("/api/start", {
      method: "POST",
      headers: {
        "content-type": "application/json"
      },
      body: JSON.stringify({
        chain,
        country,
        category,
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
      subtitle: `The export is running. We are searching for ${getCategoryLabel(category).toLowerCase()} matching ${chain} in ${country}.`,
      actionsUrl: data.actionsUrl,
      meta: [
        { label: "Chain", value: chain },
        { label: "Country", value: country },
        { label: "Category", value: getCategoryLabel(category) }
      ]
    });

    startPolling({
      fileName: data.fileName,
      actionsUrl: data.actionsUrl,
      chain,
      country,
      category
    });
  } catch (error) {
    showError(error.message);
  } finally {
    submitButton.disabled = false;
  }
});

function startPolling({ fileName, actionsUrl, chain, country, category }) {
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
        .replace("{chain}", chain)
        .replace("{country}", country)
        .replace("{category}", getCategoryLabel(category).toLowerCase()),
      actionsUrl,
      meta: [
        { label: "Chain", value: chain },
        { label: "Country", value: country },
        { label: "Category", value: getCategoryLabel(category) }
      ]
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
          chain,
          country,
          category
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
          meta: [
            { label: "Chain", value: chain },
            { label: "Country", value: country },
            { label: "Category", value: getCategoryLabel(category) }
          ]
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
      subtitle: "We are searching for {category} matching {chain} in {country}."
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

function renderReady({ fileName, downloadUrl, size, actionsUrl, chain, country, category }) {
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
        <div>
          <span>Chain</span>
          <strong>${escapeHtml(chain)}</strong>
        </div>
        <div>
          <span>Country</span>
          <strong>${escapeHtml(country)}</strong>
        </div>
        <div>
          <span>Category</span>
          <strong>${escapeHtml(getCategoryLabel(category))}</strong>
        </div>
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
        The CSV includes chain, category, address fields, formatted address, coordinates and source identifiers.
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

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;"
  }[char]));
}
