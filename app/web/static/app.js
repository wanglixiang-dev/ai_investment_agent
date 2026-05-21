const form = document.querySelector("#research-form");
const submitButton = document.querySelector("#submit-button");
const statusEl = document.querySelector("#status");
const reportTitle = document.querySelector("#report-title");
const reportEl = document.querySelector("#report");
const stepsEl = document.querySelector("#steps");
const sourcesEl = document.querySelector("#sources");
const errorsEl = document.querySelector("#errors");
const markdownLink = document.querySelector("#markdown-link");

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const payload = {
    ticker: document.querySelector("#ticker").value.trim().toUpperCase(),
    horizon: document.querySelector("#horizon").value,
    risk_level: document.querySelector("#risk-level").value,
  };

  setLoading(true);
  setStatus("Running LangGraph workflow...", false);

  try {
    const response = await fetch("/graph/research", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({}));
      throw new Error(errorBody.detail || `Request failed with ${response.status}`);
    }

    const data = await response.json();
    renderReport(data);
    setStatus(`Saved report ${data.report_id}.`, false);
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    setLoading(false);
  }
});

function renderReport(data) {
  reportTitle.textContent = `${data.ticker} Research Report`;
  reportEl.textContent = data.final_report;
  renderList(stepsEl, data.steps.map((step) => `${step.name}: ${step.status} - ${step.message}`));
  renderList(sourcesEl, data.data_sources);
  renderList(errorsEl, data.errors);

  if (data.report_id) {
    markdownLink.href = `/reports/${data.report_id}/markdown`;
    markdownLink.classList.remove("hidden");
  } else {
    markdownLink.classList.add("hidden");
  }
}

function renderList(element, values) {
  element.innerHTML = "";
  for (const value of values || []) {
    const item = document.createElement("li");
    item.textContent = value;
    element.appendChild(item);
  }
}

function setLoading(isLoading) {
  submitButton.disabled = isLoading;
  submitButton.textContent = isLoading ? "Generating..." : "Generate Report";
}

function setStatus(message, isError) {
  statusEl.textContent = message;
  statusEl.classList.toggle("error", isError);
}
