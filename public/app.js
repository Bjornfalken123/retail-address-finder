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
    title: "Starting export",
    text: "We send your request to the export engine."
  },
  {
    title: "Fetching data",
    text: "We search for matching locations in the selected category."
  },
  {
    title: "Processing addresses",
    text: "We clean the results, remove duplicates and standardize address data."
  },
  {
    title: "Creating CSV",
    text: "We prepare the file for download."
  },
  {
    title: "Ready",
    text: "Your CSV file is ready to download."
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
    showError("Please enter both chain and country.");
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
    title: "Starting export",
    subtitle: `Preparing export for ${chain} in ${country}.`
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
      badge: "Working",
      title: "Fetching data",
      subtitle: `The export has started. We are fetching ${getCategoryLabel(category).toLowerCase()} for ${chain} in ${country}.`,
      actionsUrl: data.actionsUrl
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
      actionsUrl
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
          actionsUrl
        });
      }

      if (attempts >= maxAttempts) {
        clearInterval(pollTimer);
        pollTimer = null;
        setChip("Taking longer", "slow");

        renderStatus({
          currentStep: 3,
          progress: 82,
          badge: "Taking longer",
          title: "The export is taking longer than expected",
          subtitle: "The job may still complete. You can open GitHub Actions for technical details.",
          actionsUrl
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
      badge: "Fetching",
      title: "Fetching data",
      subtitle: "We are searching for {category} for {chain} in {country}."
    };
  }

  if (attempts <= 5) {
    return {
      step: 2,
      progress: 58,
      badge: "Processing",
      title: "Processing addresses",
      subtitle: "We are cleaning, deduplicating and standardizing the results."
    };
  }

  return {
    step: 3,
    progress: 78,
    badge: "Creating file",
    title: "Creating CSV",
    subtitle: "We are preparing the file. It will appear here as soon as it is ready."
  };
}

function renderStatus({ currentStep, progress, badge, title, subtitle, actionsUrl }) {
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
        <p class="smallText">
          The export runs in the background. <a href="${actionsUrl}" target="_blank" rel="noreferrer">Open technical log in GitHub Actions</a>
        </p>
      ` : ""}
    </div>
  `;
}

function renderReady({ fileName, downloadUrl, size, actionsUrl }) {
  const sizeText = size ? `${Math.max(1, Math.round(size / 1024))} KB` : "CSV";

  result.className = "result";

  result.innerHTML = `
    <div class="readyBox">
      <div class="statusTitle">
        <div>
          <h3>CSV file is ready</h3>
          <p>The export is complete and ready to download.</p>
        </div>
        <div class="statusBadge">Ready</div>
      </div>

      <div class="progressTrack">
        <div class="progressBar" style="width: 100%"></div>
      </div>

      <div class="fileCard">
        <strong>${escapeHtml(fileName)}</strong>
        <span>${escapeHtml(sizeText)}</span>
      </div>

      <a class="downloadButton" href="${downloadUrl}">
        Download CSV
      </a>

      <p class="smallText">
        The file is also saved in GitHub under <strong>exports</strong>.
        <br>
        <a href="${actionsUrl}" target="_blank" rel="noreferrer">View run in GitHub Actions</a>
      </p>
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
