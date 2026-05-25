const form = document.querySelector("#exportForm");
const result = document.querySelector("#result");
const chainInput = document.querySelector("#chain");
const countryInput = document.querySelector("#country");

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
  const submitButton = form.querySelector("button");

  result.classList.remove("hidden");
  result.innerHTML = `
    <strong>Startar exporten...</strong><br>
    Skickar request till GitHub Actions.
  `;

  submitButton.disabled = true;

  try {
    const response = await fetch("/api/start", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        chain,
        country,
        format: "CSV",
        source: "OpenStreetMap"
      })
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Något gick fel.");
    }

    result.innerHTML = `
      <strong>Exporten är startad.</strong><br>
      Kedja: ${escapeHtml(chain)}<br>
      Land: ${escapeHtml(country)}<br><br>
      Exporten körs nu i GitHub Actions. När den är klar hittar du CSV-filen i <strong>exports</strong>-mappen i GitHub, eller som artifact under körningen.<br><br>
      <a href="${data.actionsUrl}" target="_blank" rel="noreferrer">Öppna GitHub Actions</a>
    `;
  } catch (error) {
    result.innerHTML = `
      <strong>Fel:</strong><br>
      ${escapeHtml(error.message)}
    `;
  } finally {
    submitButton.disabled = false;
  }
});

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;"
  }[char]));
}
