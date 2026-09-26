const $ = (selector) => document.querySelector(selector);
const escapeHtml = (value) => String(value).replace(/[&<>'"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[character]));

const readinessLabels = {
  core_analysis: ["Core analysis", "Feature pipeline and representation are available."],
  deterministic_demo: ["Deterministic demo", "Prepared scenarios produce stable, meaningfully separated results."],
  documentation: ["Documentation", "Method, limitations and runbook are present."],
  real_dataset: ["Permission-backed dataset", "Commit-pinned author labels include license or permission metadata."],
  held_out_evaluation: ["Held-out evaluation", "Metrics come from authors excluded from both sides of training pairs."],
  trained_fusion: ["Trained fusion", "The selected model matches the active representation."],
};

function renderReadiness(readiness) {
  const badge = $("#readiness-badge");
  badge.textContent = readiness.excellent_tier_evidence_ready ? "Competition evidence ready" : readiness.demo_ready ? "Demo ready · evidence pending" : "Action required";
  badge.className = `readiness-badge ${readiness.excellent_tier_evidence_ready ? "ready" : "pending"}`;
  $("#readiness-copy").textContent = readiness.excellent_tier_evidence_ready
    ? "Every implementation and evidence gate is backed by a checked artifact."
    : "The working prototype and external evaluation evidence are tracked separately.";
  $("#readiness-grid").innerHTML = Object.entries(readiness.gates).map(([key, gate]) => {
    const [label, detail] = readinessLabels[key] || [key.replaceAll("_", " "), "Readiness gate."];
    return `<div class="readiness-gate ${gate.passed ? "passed" : "pending"}"><span class="gate-state">${gate.passed ? "✓ Passed" : "○ Pending"}</span><strong>${escapeHtml(label)}</strong><small>${escapeHtml(detail)}</small></div>`;
  }).join("");
  const metricsPanel = $("#evidence-metrics");
  const summary = readiness.evaluation_summary;
  metricsPanel.hidden = !summary?.metrics;
  if (summary?.metrics) {
    const metrics = summary.metrics;
    metricsPanel.innerHTML = [[summary.dataset.authors, "Author labels"], [Number(metrics.roc_auc).toFixed(3), "Held-out ROC-AUC"], [Number(metrics.f1).toFixed(3), "Held-out F1"], [Number(metrics.calibrated_false_positive_rate ?? metrics.false_positive_rate).toFixed(3), "Calibrated false-positive rate"]]
      .map(([value, label]) => `<div class="evidence-metric"><strong>${escapeHtml(value)}</strong><span>${escapeHtml(label)}</span></div>`).join("");
  }
  $("#readiness-next").innerHTML = `<strong>Release action:</strong> ${escapeHtml(readiness.next_action)}`;
}

fetch("/api/readiness", { headers: { "Content-Type": "application/json" } })
  .then((response) => response.json())
  .then(renderReadiness)
  .catch(() => {
    $("#readiness-badge").textContent = "Readiness unavailable";
    $("#readiness-next").textContent = "The readiness endpoint could not be reached.";
  });
