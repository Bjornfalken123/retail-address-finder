const form = document.querySelector("#exportForm");
const result = document.querySelector("#result");
const chainInput = document.querySelector("#chain");
const countryInput = document.querySelector("#country");

let pollTimer = null;

document.querySelectorAll(".example").forEach((button) => {
  button.addEventListener("click", () => {
    chainInput.value = button.dataset.chain;
    countryInput.value = button.dataset.country;
    chainInput.focus();
  });
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const chain = chainInput.value.trim();
  const country = countryInput.value.trim();

  if (!chain || !country) {
    showResult("Fyll i både kedja och land.", "error");
    return;
  }

  const submitButton = form.querySelector("button");
  submitButton.disabled = true;

  showStatus({
    title: "Startar export",
    message: "Skickar request till GitHub Actions...",
    step: 1
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
        format: "CSV",
        source: "OpenStreetMap"
      })
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Kunde inte starta exporten.");
    }

    showStatus({
      title: "Exporten är startad",
      message: "GitHub Actions kör hämtningen. Vi kontrollerar när filen är klar.",
      step: 2,
      actionsUrl: data.actionsUrl
    });

    startPolling(data.fileName, data.actionsUrl);

  } catch (error) {
    showResult(`<strong>Fel:</strong> ${escapeHtml(error.message)}`, "error");
  } finally {
    submitButton.disabled = false;
  }
});

function startPolling(fileName, actionsUrl) {
  if (pollTimer) {
    clearInterval(pollTimer);
  }

  let attempts = 0;
  const maxAttempts = 120;

  pollTimer = setInterval(async () => {
    attempts += 1;

    showStatus({
      title: "Exporten körs",
      message: `Kontrollerar om CSV-filen är klar... (${attempts})`,
      step: 3,
      actionsUrl
    });

    try {
      const response = await fetch(`/api/status?file=${encodeURIComponent(fileName)}`);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Kunde inte läsa status.");
      }

      if (data.ready) {
        clearInterval(pollTimer);
        pollTimer = null;

        showReady({
          fileName,
          downloadUrl: data.downloadUrl,
          size: data.size,
          actionsUrl
        });
      }

      if (attempts >= maxAttempts) {
        clearInterval(pollTimer);
        pollTimer = null;

        showStatus({
          title: "Exporten tar längre tid än väntat",
          message: "Öppna GitHub Actions för att följa körningen. Filen kan fortfarande bli klar.",
          step: 3,
          actionsUrl
        });
      }
    } catch (error) {
      clearInterval(pollTimer);
      pollTimer = null;
      showResult(`<strong>Statusfel:</strong> ${escapeHtml(error.message)}`, "error");
    }
  }, 7000);
}

function showStatus({ title, message, step, actionsUrl }) {
  result.classList.remove("hidden");

  const steps = [
    { id: 1, label: "Startar" },
    { id: 2, label: "Kör export" },
    { id: 3, label: "Kontrollerar fil" },
    { id: 4, label: "Klar" }
  ];

  result.innerHTML = `
    <div class="statusBox">
      <h3>${escapeHtml(title)}</h3>
      <p>${escapeHtml(message)}</p>

      <div class="steps">
        ${steps.map((item) => `
          <div class="step ${item.id <= step ? "active" : ""}">
            <span>${item.id}</span>
            <small>${item.label}</small>
          </div>
        `).join("")}
      </div>

      ${actionsUrl ? `
        <p class="smallText">
          <a href="${actionsUrl}" target="_blank" rel="noreferrer">Öppna GitHub Actions</a>
        </p>
      ` : ""}
    </div>
  `;
}

function showReady({ fileName, downloadUrl, size, actionsUrl }) {
  const sizeText = size ? `${Math.round(size / 1024)} KB` : "CSV";

  result.classList.remove("hidden");
  result.innerHTML = `
    <div class="statusBox ready">
      <h3>CSV-filen är klar</h3>
      <p>Exporten har skapats och kan laddas ner direkt.</p>

      <div class="fileCard">
        <strong>${escapeHtml(fileName)}</strong>
        <span>${escapeHtml(sizeText)}</span>
      </div>

      <a class="downloadButton" href="${downloadUrl}">
        Download CSV
      </a>

      <p class="smallText">
        <a href="${actionsUrl}" target="_blank" rel="noreferrer">Visa körningen i GitHub Actions</a>
      </p>
    </div>
  `;
}

function showResult(html, type = "info") {
  result.classList.remove("hidden");
  result.innerHTML = `<div class="${type}">${html}</div>`;
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
