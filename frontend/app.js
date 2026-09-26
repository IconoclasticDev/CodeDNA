const $ = (selector) => document.querySelector(selector);
const state = { profile: null, report: null, model: null, historyFiles: [], submissionFiles: [], historyArchive: null, submissionArchive: null };
const escapeHtml = (value) => String(value).replace(/[&<>'"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[character]));

function startProgress(selector, messages) {
  const element = $(selector);
  let index = 0;
  element.textContent = messages[index];
  const timer = setInterval(() => {
    index = Math.min(index + 1, messages.length - 1);
    element.textContent = messages[index];
  }, 850);
  return () => { clearInterval(timer); element.textContent = ""; };
}

async function api(path, options = {}) {
  const response = await fetch(path, { headers: { "Content-Type": "application/json" }, ...options });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error?.message || "Request failed.");
  return payload;
}

function showPanel(name) {
  document.querySelectorAll(".panel").forEach((panel) => panel.classList.toggle("active", panel.id === `${name}-panel`));
  document.querySelectorAll(".step").forEach((step) => step.classList.toggle("active", step.dataset.step === name));
  $(".workspace").scrollIntoView({ behavior: "smooth", block: "start" });
}

async function readFiles(fileList) {
  const valid = [...fileList].filter((file) => file.name.toLowerCase().endsWith(".py"));
  return Promise.all(valid.map(async (file) => ({ name: file.name, content: await file.text() })));
}

async function readArchive(fileList) {
  const archive = [...fileList].find((file) => file.name.toLowerCase().endsWith(".zip"));
  if (!archive) return null;
  const bytes = new Uint8Array(await archive.arrayBuffer());
  let binary = "";
  for (let start = 0; start < bytes.length; start += 0x8000) {
    binary += String.fromCharCode(...bytes.subarray(start, start + 0x8000));
  }
  return btoa(binary);
}

function profileInputReady() {
  const repositoryPattern = /^https:\/\/github\.com\/[\w.-]+\/[\w.-]+\/?$/;
  const repositories = [...document.querySelectorAll(".repository-url")].map((input) => input.value.trim()).filter(Boolean);
  const repositoriesValid = repositories.every((url) => repositoryPattern.test(url));
  const hasSource = state.historyFiles.length >= 10 || Boolean(state.historyArchive) || repositories.length > 0;
  return hasSource && repositoriesValid;
}

function payloadFor(type) {
  const isHistory = type === "history";
  const payload = { files: state[isHistory ? "historyFiles" : "submissionFiles"] };
  const archive = state[isHistory ? "historyArchive" : "submissionArchive"];
  if (archive) payload.archive_base64 = archive;
  if (isHistory) {
    payload.repository_urls = [...document.querySelectorAll(".repository-url")].map((input) => input.value.trim()).filter(Boolean);
  }
  return payload;
}

function bindDropzone(zoneSelector, inputSelector, type) {
  const zone = $(zoneSelector);
  const input = $(inputSelector);
  const update = async (files) => {
    state[type] = await readFiles(files);
    const archiveKey = type === "historyFiles" ? "historyArchive" : "submissionArchive";
    state[archiveKey] = await readArchive(files);
    const summary = type === "historyFiles" ? $("#history-summary") : $("#submission-summary");
    const button = type === "historyFiles" ? $("#build-profile") : $("#analyze-submission");
    const pieces = [];
    if (state[type].length) pieces.push(`${state[type].length} Python file${state[type].length === 1 ? "" : "s"}`);
    if (state[archiveKey]) pieces.push("1 ZIP archive");
    summary.textContent = pieces.length ? `${pieces.join(" + ")} ready` : "No source selected";
    button.disabled = type === "historyFiles" ? !profileInputReady() : !(state[type].length || state[archiveKey]);
  };
  input.addEventListener("change", () => update(input.files));
  ["dragenter", "dragover"].forEach((event) => zone.addEventListener(event, (e) => { e.preventDefault(); zone.classList.add("dragging"); }));
  ["dragleave", "drop"].forEach((event) => zone.addEventListener(event, (e) => { e.preventDefault(); zone.classList.remove("dragging"); }));
  zone.addEventListener("drop", (e) => update(e.dataTransfer.files));
}

function renderProfile(profile) {
  state.profile = profile;
  $("#profile-title").textContent = profile.name;
  $("#confidence-badge").textContent = `${profile.confidence} confidence`;
  const stats = [
    [profile.files_analyzed, "files"], [profile.functions_analyzed, "functions"],
    [profile.lines_analyzed, "lines"], [profile.duplicates_removed, "duplicates removed"],
  ];
  $("#profile-stats").innerHTML = stats.map(([value, label]) => `<div class="stat"><strong>${value}</strong><span>${label}</span></div>`).join("");
  const labels = { lexical: "Lexical habits", structural: "AST structure", complexity: "Complexity" };
  $("#stability-bars").innerHTML = Object.entries(profile.group_stability).map(([key, value]) => `
    <div class="signal"><div class="signal-label"><span>${labels[key]}</span><span>${value}%</span></div>
    <div class="track"><div class="fill" style="width:${value}%"></div></div></div>`).join("");
  $("#profile-warning").textContent = profile.warnings?.[0] || "";
  showPanel("fingerprint");
}

function component(label, value) {
  const shown = value == null ? "Pending" : `${value}%`;
  const width = value == null ? 0 : value;
  return `<div class="component"><div class="component-head"><span>${label}</span><span>${shown}</span></div><div class="track"><div class="fill" style="width:${width}%"></div></div></div>`;
}

function deviationLabel(item) {
  const value = item.deviation_score ?? item.z_score ?? 0;
  const prefix = value > 0 ? "+" : "";
  return `${item.deviation_capped ? (value > 0 ? ">" : "<") : ""}${prefix}${value}`;
}

function renderReport(report) {
  state.report = report;
  $("#score-value").textContent = Math.round(report.score);
  $("#ring-score").textContent = Math.round(report.score);
  $("#score-ring").style.setProperty("--score", `${report.score}%`);
  $("#verdict").textContent = report.verdict;
  $("#model-meta").textContent = `${report.model.name} · ${report.model.trained ? "trained fusion active" : "uncalibrated baseline"}`;
  $("#components").innerHTML = [
    component("Lexical style", report.components.lexical), component("AST structure", report.components.structural),
    component("Complexity", report.components.complexity), component(report.representation.startsWith("codebert") ? "Frozen CodeBERT" : "AST-token representation", report.components.semantic),
  ].join("");
  const gap = report.surface_structure_gap;
  $("#gap-value").textContent = `${gap >= 0 ? "+" : ""}${gap} pts`;
  $("#gap-copy").textContent = gap > 10
    ? "Surface naming is considerably more familiar than deeper program behaviour. This disagreement deserves review."
    : "Surface and deeper program signals do not show a large disagreement in this submission.";
  const fileBreakdown = report.file_breakdown || [];
  const fileMapSection = $("#file-map-section");
  fileMapSection.hidden = fileBreakdown.length < 2;
  if (fileBreakdown.length >= 2) {
    $("#file-map-copy").textContent = `Lowest-consistency files first${report.file_breakdown_total > fileBreakdown.length ? ` · showing ${fileBreakdown.length} of ${report.file_breakdown_total}` : ""}. File scores guide review; the overall verdict remains submission-level.`;
    $("#file-map").innerHTML = fileBreakdown.map((item) => {
      const verdictClass = item.verdict.toLowerCase().replaceAll(" ", "-");
      return `<div class="file-row">
        <strong class="file-name" title="${escapeHtml(item.name)}">${escapeHtml(item.name)}</strong>
        <div class="file-meter" aria-label="${escapeHtml(item.name)} consistency ${item.score} percent"><span style="width:${item.score}%"></span></div>
        <span class="file-score">${item.score}</span>
        <span class="file-verdict ${verdictClass}">${escapeHtml(item.verdict)}</span>
      </div>`;
    }).join("");
  }
  const functionBreakdown = report.function_breakdown || [];
  const functionMapSection = $("#function-map-section");
  functionMapSection.hidden = functionBreakdown.length === 0;
  if (functionBreakdown.length) {
    $("#function-map-copy").textContent = `Highest engineered deviation first${report.function_breakdown_total > functionBreakdown.length ? ` · showing ${functionBreakdown.length} of ${report.function_breakdown_total}` : ""}. This map explains the result and does not alter the trained score.`;
    $("#function-map").innerHTML = functionBreakdown.map((item) => {
      const signals = [["Lexical", item.signals.lexical], ["Structure", item.signals.structural], ["Complexity", item.signals.complexity]];
      return `<div class="function-row" title="Strongest shift: ${escapeHtml(item.strongest_feature)}">
        <div class="function-identity"><strong>${escapeHtml(item.function)}()</strong><span>${escapeHtml(item.file)} · lines ${item.line_start}–${item.line_end}</span></div>
        <div class="function-signals">${signals.map(([label, value]) => `<div class="function-signal" style="--heat-number:${Math.round(value)}"><i></i><span>${label} ${Math.round(value)}</span></div>`).join("")}</div>
        <div class="function-index"><strong>${Math.round(item.deviation_index)}</strong><span>deviation</span></div>
      </div>`;
    }).join("");
  }
  $("#deviations").innerHTML = report.top_deviations.map((item) => `
    <div class="deviation"><strong>${item.label}</strong><span>History ${item.historical}</span><span>Submission ${item.submission}</span><div class="z" title="${escapeHtml(item.scale_method || "normalized deviation")}">${deviationLabel(item)} index</div></div>`).join("");
  $("#notice").textContent = report.notice;
  const coverage = report.coverage;
  $("#coverage-card").innerHTML = [
    [coverage.files_analyzed, "files analyzed"], [coverage.files_skipped, "files skipped"], [coverage.duplicates_removed, "duplicates removed"],
  ].map(([value, label]) => `<div class="coverage-item"><strong>${value}</strong><span>${label}</span></div>`).join("");
  $("#report-warnings").innerHTML = (report.warnings || []).map((warning) => `<div class="report-warning">${escapeHtml(warning)}</div>`).join("");
  showPanel("report");
}

function reportHtml(report, profile) {
  const components = [
    ["Lexical style", report.components.lexical],
    ["AST structure", report.components.structural],
    ["Complexity", report.components.complexity],
    [report.representation.startsWith("codebert") ? "Frozen CodeBERT" : "AST-token representation", report.components.semantic],
  ];
  const componentRows = components.map(([label, value]) => `<tr><td>${escapeHtml(label)}</td><td>${value == null ? "Unavailable" : `${Number(value).toFixed(1)}%`}</td></tr>`).join("");
  const deviationRows = report.top_deviations.map((item) => `<tr>
    <td>${escapeHtml(item.label)}</td><td>${escapeHtml(item.historical)}</td>
    <td>${escapeHtml(item.submission)}</td><td>${escapeHtml(deviationLabel(item))}</td>
  </tr>`).join("");
  const warnings = (report.warnings || []).length
    ? `<section><h2>Analysis warnings</h2><ul>${report.warnings.map((warning) => `<li>${escapeHtml(warning)}</li>`).join("")}</ul></section>`
    : "";
  const fileRows = (report.file_breakdown || []).map((item) => `<tr><td>${escapeHtml(item.name)}</td><td>${item.score}</td><td>${escapeHtml(item.verdict)}</td><td>${item.surface_structure_gap >= 0 ? "+" : ""}${item.surface_structure_gap}</td></tr>`).join("");
  const fileSection = fileRows ? `<section><h2>File-level review map</h2><p class="meta">Lowest-consistency files appear first. The overall verdict remains submission-level.</p><table><thead><tr><th>File</th><th>Score</th><th>Verdict</th><th>Surface / structure gap</th></tr></thead><tbody>${fileRows}</tbody></table></section>` : "";
  const functionRows = (report.function_breakdown || []).map((item) => `<tr><td>${escapeHtml(item.file)}</td><td>${escapeHtml(item.function)}()</td><td>${item.line_start}–${item.line_end}</td><td>${item.deviation_index}</td><td>${escapeHtml(item.strongest_feature)}</td></tr>`).join("");
  const functionSection = functionRows ? `<section><h2>Function-level review map</h2><p class="meta">Highest engineered deviation first. This explanatory map does not alter the trained score.</p><table><thead><tr><th>File</th><th>Function</th><th>Lines</th><th>Deviation</th><th>Strongest shift</th></tr></thead><tbody>${functionRows}</tbody></table></section>` : "";
  const generated = new Date().toISOString();
  return `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>CodeDNA review report — ${escapeHtml(profile?.name || report.profile_id)}</title>
<style>
:root{--ink:#151512;--muted:#62635d;--paper:#f4f1e8;--card:#fff;--violet:#6952e8;--acid:#d9ff58;--line:#d9d4c6}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.55 Arial,sans-serif}.page{max-width:920px;margin:32px auto;background:var(--card);padding:48px;border:1px solid var(--line)}header{display:flex;justify-content:space-between;gap:30px;border-bottom:3px solid var(--ink);padding-bottom:25px}.brand{font-weight:800;font-size:22px}.tag{font:12px monospace;color:var(--violet);text-transform:uppercase}.score{font:700 64px/1 monospace;letter-spacing:-5px}.score small{font-size:18px;letter-spacing:0;color:var(--muted)}.verdict{display:inline-block;margin-top:10px;padding:7px 10px;background:var(--ink);color:#fff;font:12px monospace;text-transform:uppercase}section{margin-top:34px}h1{font-size:34px;margin:8px 0}h2{font-size:20px;margin-bottom:12px}p.meta{color:var(--muted);font-size:12px}table{width:100%;border-collapse:collapse}th,td{padding:11px 12px;border:1px solid var(--line);text-align:left}th{background:#f4f1e8;font-size:12px;text-transform:uppercase}.gap{padding:18px;background:var(--ink);color:#fff}.gap strong{color:var(--acid);float:right}.notice{padding:16px;border-left:4px solid var(--violet);background:#eeeafc}.coverage{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.coverage div{padding:15px;border:1px solid var(--line)}.coverage strong{display:block;font:24px monospace}.coverage span{color:var(--muted);font-size:11px;text-transform:uppercase}footer{margin-top:40px;padding-top:18px;border-top:1px solid var(--line);color:var(--muted);font-size:11px}@media print{body{background:#fff}.page{margin:0;border:0;max-width:none;padding:24px}button{display:none}}@media(max-width:650px){.page{margin:0;padding:25px}header{display:block}.score{margin-top:22px}.coverage{grid-template-columns:1fr}}
</style></head><body><main class="page">
<header><div><div class="brand">CodeDNA</div><div class="tag">Behavioural code-authentication evidence</div><h1>${escapeHtml(profile?.name || "Developer profile")}</h1><p class="meta">Profile ${escapeHtml(report.profile_id)} · Generated ${escapeHtml(generated)} · ${escapeHtml(report.model.name)}</p></div><div><div class="score">${Math.round(report.score)}<small>/100</small></div><div class="verdict">${escapeHtml(report.verdict)}</div></div></header>
<section><h2>Signal agreement</h2><table><thead><tr><th>Signal family</th><th>Consistency</th></tr></thead><tbody>${componentRows}</tbody></table></section>
<section class="gap"><span>Surface / structure gap</span><strong>${report.surface_structure_gap >= 0 ? "+" : ""}${escapeHtml(report.surface_structure_gap)} pts</strong><p>${report.surface_structure_gap > 10 ? "Surface naming is considerably more familiar than deeper program behaviour. This disagreement deserves review." : "Surface and deeper program signals do not show a large disagreement."}</p></section>
${fileSection}
${functionSection}
<section><h2>Largest behavioural deviations</h2><table><thead><tr><th>Feature</th><th>History</th><th>Submission</th><th>Deviation index</th></tr></thead><tbody>${deviationRows}</tbody></table></section>
<section><h2>Analysis coverage</h2><div class="coverage"><div><strong>${report.coverage.files_analyzed}</strong><span>Files analyzed</span></div><div><strong>${report.coverage.files_skipped}</strong><span>Files skipped</span></div><div><strong>${report.coverage.duplicates_removed}</strong><span>Duplicates removed</span></div></div></section>
${warnings}<section class="notice"><strong>Interpretation boundary</strong><p>${escapeHtml(report.notice)}</p></section>
<footer>Representation: ${escapeHtml(report.representation)} · This standalone report contains derived evidence and no submitted source code.</footer>
</main></body></html>`;
}

function downloadBlob(content, type, filename) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

async function runDemo(caseName) {
  const button = $(`#demo-${caseName}`);
  const original = button.innerHTML;
  button.disabled = true;
  button.textContent = "Building fingerprint…";
  try {
    const data = await api(`/api/demo/${caseName}`);
    renderProfile(data.profile);
    const transition = $("#demo-transition");
    transition.innerHTML = "<strong>Fingerprint ready.</strong> Preparing the submission comparison and evidence report…";
    await new Promise((resolve) => setTimeout(resolve, 1600));
    transition.textContent = "";
    renderReport(data.report);
  } catch (error) {
    alert(error.message);
  } finally {
    button.disabled = false;
    button.innerHTML = original;
  }
}

bindDropzone("#history-dropzone", "#history-files", "historyFiles");
bindDropzone("#submission-dropzone", "#submission-files", "submissionFiles");

$("#build-profile").addEventListener("click", async () => {
  const button = $("#build-profile"); const error = $("#profile-error");
  error.textContent = ""; button.disabled = true; button.textContent = "Extracting behavioural signals…";
  const stopProgress = startProgress("#profile-processing", ["Validating sources", "Filtering eligible Python", "Extracting behaviour signals", "Building profile statistics"]);
  try {
    const profile = await api("/api/profiles", { method: "POST", body: JSON.stringify({ name: $("#developer-name").value, ...payloadFor("history") }) });
    renderProfile(profile);
  } catch (err) { error.textContent = err.message; }
  finally { stopProgress(); button.disabled = !profileInputReady(); button.innerHTML = "Build behavioural profile <span>→</span>"; }
});

$("#analyze-submission").addEventListener("click", async () => {
  const button = $("#analyze-submission"); const error = $("#submission-error");
  error.textContent = ""; button.disabled = true; button.textContent = "Comparing behavioural signals…";
  const stopProgress = startProgress("#submission-processing", ["Validating submission", "Extracting four signal families", "Comparing historical distributions", "Preparing evidence report"]);
  try {
    const submission = payloadFor("submission");
    submission.profile_context = state.profile.analysis_context;
    const report = await api(`/api/profiles/${state.profile.id}/analyze`, { method: "POST", body: JSON.stringify(submission) });
    renderReport(report);
  } catch (err) { error.textContent = err.message; }
  finally { stopProgress(); button.disabled = false; button.innerHTML = "Analyze consistency <span>→</span>"; }
});

$("#demo-review").addEventListener("click", () => runDemo("review"));
$("#demo-consistent").addEventListener("click", () => runDemo("consistent"));
$("#demo-mixed").addEventListener("click", () => runDemo("mixed"));
document.querySelectorAll(".step").forEach((step) => step.addEventListener("click", () => {
  const target = step.dataset.step;
  if (target === "profile" || (target === "fingerprint" && state.profile) || (target === "report" && state.report)) {
    showPanel(target);
  }
}));
$("#new-analysis").addEventListener("click", () => showPanel("fingerprint"));
$("#restart").addEventListener("click", () => location.reload());
$("#repository-list").addEventListener("input", () => { $("#build-profile").disabled = !profileInputReady(); });
$("#repository-list").addEventListener("click", (event) => {
  const remove = event.target.closest(".remove-repository");
  if (!remove || document.querySelectorAll(".repository-row").length === 1) return;
  remove.closest(".repository-row").remove();
  $("#add-repository").disabled = false;
  $("#build-profile").disabled = !profileInputReady();
});
$("#add-repository").addEventListener("click", () => {
  const list = $("#repository-list");
  const count = list.querySelectorAll(".repository-row").length;
  if (count >= 4) return;
  const row = document.createElement("div");
  row.className = "repository-row";
  row.innerHTML = `<input class="text-input repository-url" aria-label="Public GitHub repository ${count + 1}" placeholder="https://github.com/owner/repository" autocomplete="off" /><button class="remove-repository" type="button" aria-label="Remove repository">×</button>`;
  list.appendChild(row);
  if (count === 3) $("#add-repository").disabled = true;
});
$("#download-report").addEventListener("click", () => {
  if (!state.report) return;
  downloadBlob(JSON.stringify(state.report, null, 2), "application/json", `codedna-${state.report.profile_id}-evidence.json`);
});
$("#download-html").addEventListener("click", () => {
  if (!state.report) return;
  downloadBlob(reportHtml(state.report, state.profile), "text/html", `codedna-${state.report.profile_id}-review.html`);
});

api("/api/health").then((health) => {
  $("#system-status").textContent = health.status === "ready" ? "Core analysis ready" : "System degraded";
  $(".status").classList.toggle("ready", health.status === "ready");
}).catch(() => { $("#system-status").textContent = "System unavailable"; });
api("/api/model").then((model) => { state.model = model; }).catch(() => {});


