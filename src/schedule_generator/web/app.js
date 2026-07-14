const state = { datasets: [], jobs: [], dataset: null, collection: "classes", poller: null };
const collections = [
  ["classes", "Classes"], ["teachers", "Teachers"], ["subjects", "Subjects"],
  ["classrooms", "Classrooms"], ["groups", "Groups"], ["cohorts", "Cohorts"],
  ["curriculum_requirements", "Curriculum"], ["resource_availability", "Availability"]
];
const titles = { overview: "Overview", data: "School data", rules: "Rules", generate: "Generate", results: "Results" };

function html(value) {
  return String(value).replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character]);
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) }
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.detail || payload.error || "Request failed");
  return payload;
}

function notice(message, error = false) {
  const element = document.querySelector("#notice");
  element.textContent = message;
  element.classList.toggle("error", error);
  element.hidden = false;
  clearTimeout(notice.timer);
  notice.timer = setTimeout(() => { element.hidden = true; }, 4200);
}

function showView(name) {
  document.querySelectorAll(".view").forEach((view) => view.classList.toggle("active", view.id === `view-${name}`));
  document.querySelectorAll(".nav-item").forEach((item) => item.classList.toggle("active", item.dataset.view === name));
  document.querySelector("#page-title").textContent = titles[name];
  location.hash = name;
  if (name === "results") renderResults();
}

async function loadState(quiet = false) {
  try {
    const payload = await api("/api/state");
    state.datasets = payload.datasets;
    state.jobs = payload.jobs;
    state.dataset = state.datasets[0] || null;
    render();
    if (!quiet) notice("Workspace refreshed");
  } catch (error) { notice(error.message, true); }
}

function render() {
  const data = state.dataset?.data;
  document.querySelector("#empty-state").hidden = Boolean(data);
  document.querySelector("#dashboard").hidden = !data;
  document.querySelector("#dataset-badge").textContent = data ? `Revision ${state.dataset.revision} · ${data.dataset_id}` : "No dataset";
  if (!data) return;
  document.querySelector("#school-name").textContent = data.school.label;
  document.querySelector("#period-label").textContent = `${data.academic_period.label} · ${data.academic_period.start_date} — ${data.academic_period.end_date}`;
  for (const key of ["classes", "teachers", "subjects"]) document.querySelector(`#metric-${key}`).textContent = data[key].length;
  document.querySelector("#metric-requirements").textContent = data.curriculum_requirements.length;
  renderChecklist(data);
  renderJobs();
  renderEditor();
  renderRules(data);
  renderCurrentRun();
  renderJobSelect();
}

function renderChecklist(data) {
  const items = [
    ["Academic week", data.academic_period.days.length > 0],
    ["Classes and groups", data.classes.length > 0],
    ["Teachers and subjects", data.teachers.length > 0 && data.subjects.length > 0],
    ["Rooms and capabilities", data.classrooms.length > 0],
    ["Curriculum requirements", data.curriculum_requirements.length > 0]
  ];
  const ready = items.filter((item) => item[1]).length;
  document.querySelector("#readiness-score").textContent = `${Math.round(ready / items.length * 100)}%`;
  document.querySelector("#checklist").innerHTML = items.map(([label, complete]) => `<div class="check-item"><span>${label}</span><b>${complete ? "Ready" : "Missing"}</b></div>`).join("");
}

function jobCard(job) {
  return `<div class="job-card ${job.status}"><div><span>${job.status}</span><span>${job.progress.completed}/${job.progress.total}</span></div><small>Seed ${job.parameters.seed} · ${job.parameters.time_limit_seconds}s per alternative</small></div>`;
}

function renderJobs() {
  const jobs = [...state.jobs].reverse();
  document.querySelector("#recent-jobs").innerHTML = jobs.length ? jobs.slice(0, 4).map(jobCard).join("") : `<div class="run-placeholder">No jobs yet.</div>`;
}

function renderEditor() {
  if (!state.dataset) return;
  const tabs = document.querySelector("#collection-tabs");
  tabs.innerHTML = collections.map(([key, label]) => `<button class="collection-tab ${key === state.collection ? "active" : ""}" data-collection="${key}">${label}</button>`).join("");
  tabs.querySelectorAll("button").forEach((button) => button.addEventListener("click", () => { state.collection = button.dataset.collection; renderEditor(); }));
  const label = collections.find(([key]) => key === state.collection)[1];
  const records = state.dataset.data[state.collection] || [];
  document.querySelector("#editor-title").textContent = label;
  document.querySelector("#record-count").textContent = `${records.length} records`;
  document.querySelector("#collection-json").value = JSON.stringify(records, null, 2);
}

function renderRules(data) {
  document.querySelector("#difficulty-list").innerHTML = data.subjects.map((subject) => `<div class="form-row"><div><strong>${html(subject.label)}</strong><small>${html(subject.id)}</small></div><span class="level">Level ${subject.default_workload}</span></div>`).join("");
  document.querySelector("#priority-list").innerHTML = data.policies.soft_constraint_weights.map((rule) => `<div class="form-row"><div><strong>${html(rule.constraint_id)}</strong><small>${html(rule.priority)}</small></div><span class="level">Weight ${rule.weight}</span></div>`).join("");
  const summary = [
    [data.curriculum_requirements.length, "Curriculum rules"],
    [data.resource_availability.length, "Availability records"],
    [data.policies.daily_limits.length, "Daily limits"],
    [data.fixed_lessons.length, "Fixed lessons"]
  ];
  document.querySelector("#rules-summary").innerHTML = summary.map(([value, label]) => `<div><strong>${value}</strong><small>${label}</small></div>`).join("");
}

function renderCurrentRun() {
  const job = [...state.jobs].reverse().find((item) => ["PENDING", "RUNNING"].includes(item.status)) || [...state.jobs].reverse()[0];
  const target = document.querySelector("#current-run");
  if (!job) { target.innerHTML = `<div class="run-placeholder">No generation job is active.</div>`; return; }
  const progress = Math.round(job.progress.completed / Math.max(1, job.progress.total) * 100);
  target.innerHTML = `<div class="run-status"><div><p class="eyebrow">${job.status}</p><h3>${job.status === "SUCCEEDED" ? "Timetable ready" : job.status === "RUNNING" ? "Building alternatives" : "Generation job"}</h3></div><div class="progress-track"><div class="progress-fill" style="width:${progress}%"></div></div><div class="run-meta"><div><small>Progress</small><strong>${job.progress.completed} of ${job.progress.total}</strong></div><div><small>Seed</small><strong>${job.parameters.seed}</strong></div><div><small>Limit</small><strong>${job.parameters.time_limit_seconds}s</strong></div></div>${["PENDING", "RUNNING"].includes(job.status) ? `<button id="cancel-job" class="text-button">Cancel generation</button>` : `<button class="primary-button" data-go="results">Review result</button>`}</div>`;
  target.querySelector("#cancel-job")?.addEventListener("click", () => cancelJob(job.job_id));
  target.querySelector("[data-go]")?.addEventListener("click", () => showView("results"));
  if (["PENDING", "RUNNING"].includes(job.status)) startPolling(); else stopPolling();
}

function renderJobSelect() {
  const select = document.querySelector("#job-select");
  const successful = state.jobs.filter((job) => job.status === "SUCCEEDED");
  const previous = select.value;
  select.innerHTML = successful.length ? successful.map((job) => `<option value="${job.job_id}">${job.job_id.slice(0, 8)} · ${job.parameters.alternatives} alternative(s)</option>`).join("") : `<option value="">No successful jobs</option>`;
  if (successful.some((job) => job.job_id === previous)) select.value = previous;
}

function selectedJob() {
  const id = document.querySelector("#job-select").value;
  return state.jobs.find((job) => job.job_id === id) || [...state.jobs].reverse().find((job) => job.status === "SUCCEEDED");
}

function renderResults() {
  const job = selectedJob();
  document.querySelector("#no-result").hidden = Boolean(job?.result);
  document.querySelector("#result-content").hidden = !job?.result;
  if (!job?.result || !state.dataset) return;
  const report = job.result.quality_report;
  document.querySelector("#quality-chip").textContent = report ? `Quality penalty ${report.total_penalty}` : "Feasible timetable";
  const violations = report?.violations || [];
  document.querySelector("#quality-report").innerHTML = violations.length ? violations.map((item) => `<div class="quality-item"><strong>${html(item.constraint_id)} · +${item.weighted_penalty}</strong><small>${html(item.description)}</small></div>`).join("") : `<div class="check-item"><span>No preference violations</span><b>Excellent</b></div>`;
  renderResourceOptions();
  renderTimetable(job.result.assignments);
}

function renderResourceOptions() {
  const mode = document.querySelector("#view-mode").value;
  const data = state.dataset.data;
  const resources = mode === "class" ? data.classes : mode === "teacher" ? data.teachers : data.classrooms;
  const select = document.querySelector("#resource-select");
  const previous = select.value;
  select.innerHTML = resources.map((item) => `<option value="${html(item.id)}">${html(item.label)}</option>`).join("");
  if (resources.some((item) => item.id === previous)) select.value = previous;
}

function assignmentMatches(assignment, mode, resourceId) {
  if (mode === "teacher") return assignment.teacher_id === resourceId;
  if (mode === "classroom") return assignment.classroom_id === resourceId;
  const requirement = state.dataset.data.curriculum_requirements.find((item) => item.id === assignment.requirement_id);
  if (!requirement) return false;
  if (requirement.participant.type === "class") return requirement.participant.id === resourceId;
  if (requirement.participant.type === "group") return state.dataset.data.groups.find((item) => item.id === requirement.participant.id)?.class_id === resourceId;
  const cohort = state.dataset.data.cohorts.find((item) => item.id === requirement.participant.id);
  return cohort?.members.some((member) => member.type === "class" && member.id === resourceId);
}

function renderTimetable(assignments) {
  const data = state.dataset.data;
  const mode = document.querySelector("#view-mode").value;
  const resourceId = document.querySelector("#resource-select").value;
  const filtered = assignments.filter((item) => assignmentMatches(item, mode, resourceId));
  const periods = [...data.academic_period.periods].sort((a, b) => a.ordinal - b.ordinal);
  const days = [...data.academic_period.days].sort((a, b) => a.ordinal - b.ordinal);
  const cells = (day, period) => {
    const lesson = filtered.find((item) => item.slot.day_id === day.id && item.occupied_period_ids.includes(period.id));
    if (!lesson) return "";
    const requirement = data.curriculum_requirements.find((item) => item.id === lesson.requirement_id);
    const subject = data.subjects.find((item) => item.id === requirement?.subject_id)?.label || lesson.requirement_id;
    const teacher = data.teachers.find((item) => item.id === lesson.teacher_id)?.label || lesson.teacher_id;
    const room = data.classrooms.find((item) => item.id === lesson.classroom_id)?.label || lesson.classroom_id;
    return `<span class="lesson">${html(subject)}<small>${html(teacher)} · ${html(room)}</small></span>`;
  };
  document.querySelector("#timetable").innerHTML = `<table><thead><tr><th>Period</th>${days.map((day) => `<th>${html(day.label)}</th>`).join("")}</tr></thead><tbody>${periods.map((period) => `<tr><th>${html(period.label)}<br><small>${html(period.start_time)}</small></th>${days.map((day) => `<td>${cells(day, period)}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
}

async function saveCollection() {
  try {
    const records = JSON.parse(document.querySelector("#collection-json").value);
    if (!Array.isArray(records)) throw new Error("The editor must contain a JSON array");
    await api(`/api/datasets/${encodeURIComponent(state.dataset.dataset_id)}/collections/${state.collection}`, { method: "PUT", body: JSON.stringify({ records }) });
    await loadState(true);
    notice(`${collections.find(([key]) => key === state.collection)[1]} saved as a new revision`);
  } catch (error) { notice(error.message, true); }
}

async function startGeneration(event) {
  event.preventDefault();
  if (!state.dataset) return notice("Load school data first", true);
  try {
    const job = await api("/api/jobs", { method: "POST", body: JSON.stringify({
      dataset_id: state.dataset.dataset_id,
      alternatives: Number(document.querySelector("#alternatives").value),
      time_limit_seconds: Number(document.querySelector("#time-limit").value),
      seed: Number(document.querySelector("#seed").value), workers: 1
    }) });
    notice(`Generation job ${job.job_id.slice(0, 8)} started`);
    await loadState(true);
    startPolling();
  } catch (error) { notice(error.message, true); }
}

async function cancelJob(jobId) {
  try { await api(`/api/jobs/${jobId}/cancel`, { method: "POST" }); await loadState(true); notice("Cancellation requested"); }
  catch (error) { notice(error.message, true); }
}

function startPolling() {
  if (state.poller) return;
  state.poller = setInterval(() => loadState(true), 1200);
}
function stopPolling() { clearInterval(state.poller); state.poller = null; }

document.querySelectorAll(".nav-item").forEach((item) => item.addEventListener("click", () => showView(item.dataset.view)));
document.querySelectorAll("[data-go]").forEach((item) => item.addEventListener("click", () => showView(item.dataset.go)));
document.querySelector("#refresh").addEventListener("click", () => loadState());
document.querySelector("#load-demo").addEventListener("click", async () => { try { await api("/api/demo", { method: "POST" }); await loadState(true); notice("Demonstration school loaded"); } catch (error) { notice(error.message, true); } });
document.querySelector("#save-collection").addEventListener("click", saveCollection);
document.querySelector("#generation-form").addEventListener("submit", startGeneration);
document.querySelector("#job-select").addEventListener("change", renderResults);
document.querySelector("#view-mode").addEventListener("change", () => { renderResourceOptions(); renderResults(); });
document.querySelector("#resource-select").addEventListener("change", renderResults);
showView(location.hash.slice(1) in titles ? location.hash.slice(1) : "overview");
loadState(true);
