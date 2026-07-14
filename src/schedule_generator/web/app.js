const state = { datasets: [], jobs: [], drafts: [], publications: [], dataset: null, collection: "classes", poller: null };
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
    state.drafts = payload.drafts || [];
    state.publications = payload.publications || [];
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
  renderResults();
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

function selectedDraft() {
  const job = selectedJob();
  return job ? state.drafts.find((draft) => draft.job_id === job.job_id) : null;
}

function renderResults() {
  const job = selectedJob();
  document.querySelector("#no-result").hidden = Boolean(job?.result);
  document.querySelector("#result-content").hidden = !job?.result;
  if (!job?.result || !state.dataset) return;
  const draft = selectedDraft();
  const result = draft ? {
    assignments: draft.version.assignments,
    quality_report: draft.version.quality,
    validation_errors: draft.version.validation_errors
  } : job.result;
  const report = result.quality_report;
  document.querySelector("#quality-chip").textContent = report ? `Quality penalty ${report.total_penalty}` : "Feasible timetable";
  const violations = report?.violations || [];
  document.querySelector("#quality-report").innerHTML = violations.length ? violations.map((item) => `<div class="quality-item"><strong>${html(item.constraint_id)} · +${item.weighted_penalty}</strong><small>${html(item.description)}</small></div>`).join("") : `<div class="check-item"><span>No preference violations</span><b>Excellent</b></div>`;
  renderEditing(draft);
  renderPublication(draft);
  renderResourceOptions();
  renderTimetable(result.assignments, draft);
}

function changeLabel(change) {
  if (change.type === "generated") return "Generated result";
  if (change.type === "move") return `Moved ${change.assignment_id}`;
  if (change.type === "regenerate") return `Regenerated with ${change.locked_assignment_ids.length} lock(s)`;
  return change.type;
}

function renderEditing(draft) {
  const start = document.querySelector("#start-editing");
  const undo = document.querySelector("#undo-edit");
  const redo = document.querySelector("#redo-edit");
  const regenerate = document.querySelector("#regenerate-draft");
  const historyPanel = document.querySelector("#history-panel");
  const conflict = document.querySelector("#conflict-banner");
  start.hidden = Boolean(draft);
  undo.disabled = !draft || draft.current_version === 0;
  redo.disabled = !draft || draft.current_version >= draft.latest_version;
  regenerate.hidden = !draft;
  historyPanel.hidden = !draft;
  document.querySelector("#version-label").textContent = draft ? `Draft version ${draft.current_version}` : "Generated result";
  const errors = draft?.version.validation_errors || [];
  conflict.hidden = !errors.length;
  conflict.textContent = errors.length ? `${errors.length} hard conflict(s): ${errors.join(" · ")}` : "";
  if (!draft) return;
  document.querySelector("#version-history").innerHTML = [...draft.history].reverse().map((item) => `<div class="version-item ${item.version === draft.current_version ? "current" : ""}"><strong>Version ${item.version}</strong><small>${html(changeLabel(item.change))}</small></div>`).join("");
  const options = draft.history.map((item) => `<option value="${item.version}">Version ${item.version}</option>`).join("");
  const left = document.querySelector("#compare-left");
  const right = document.querySelector("#compare-right");
  left.innerHTML = options;
  right.innerHTML = options;
  left.value = "0";
  right.value = String(draft.current_version);
}

function renderPublication(draft) {
  const target = document.querySelector("#publication-status");
  if (!draft) {
    target.innerHTML = `<p>Create an editable timetable before approval.</p>`;
    return;
  }
  const publication = state.publications.find((item) => item.draft_id === draft.draft_id && item.version === draft.current_version);
  if (!publication) {
    const blocked = draft.version.validation_errors.length > 0;
    target.innerHTML = `<p>Version ${draft.current_version} is a draft${blocked ? " with unresolved conflicts" : " ready for review"}.</p><button id="approve-publication" class="primary-button" ${blocked ? "disabled" : ""}>Approve version</button>`;
    target.querySelector("#approve-publication")?.addEventListener("click", approvePublication);
    return;
  }
  if (publication.status === "APPROVED") {
    target.innerHTML = `<p><span class="status-pill approved">Approved</span> Version ${publication.version} is immutable and ready to publish.</p><button id="publish-publication" class="primary-button">Publish XLSX and PDF</button>`;
    target.querySelector("#publish-publication")?.addEventListener("click", () => changePublication(publication.publication_id, "publish"));
    return;
  }
  const links = Object.entries(publication.artifacts).map(([kind, artifact]) => `<a href="/downloads/${encodeURIComponent(artifact.filename)}">Download ${html(kind.toUpperCase())}</a>`).join("");
  if (publication.status === "PUBLISHED") {
    target.innerHTML = `<p><span class="status-pill published">Published</span> Version ${publication.version} is available for distribution.</p><div class="download-links">${links}</div><button id="unpublish-publication" class="text-button">Unpublish</button>`;
    target.querySelector("#unpublish-publication")?.addEventListener("click", () => changePublication(publication.publication_id, "unpublish"));
  } else {
    target.innerHTML = `<p><span class="status-pill unpublished">Unpublished</span> Version ${publication.version} is no longer available for download.</p><button id="republish-publication" class="primary-button">Publish again</button>`;
    target.querySelector("#republish-publication")?.addEventListener("click", () => changePublication(publication.publication_id, "publish"));
  }
}

async function approvePublication() {
  const draft = selectedDraft();
  if (!draft) return;
  try {
    await api(`/api/drafts/${draft.draft_id}/approve`, {method: "POST"});
    await loadState(true);
    notice(`Version ${draft.current_version} approved`);
  } catch (error) { notice(error.message, true); }
}

async function changePublication(publicationId, action) {
  try {
    await api(`/api/publications/${publicationId}/${action}`, {method: "POST"});
    await loadState(true);
    notice(action === "publish" ? "Timetable published" : "Timetable unpublished");
  } catch (error) { notice(error.message, true); }
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

function renderTimetable(assignments, draft = null) {
  const data = state.dataset.data;
  const mode = document.querySelector("#view-mode").value;
  const resourceId = document.querySelector("#resource-select").value;
  const filtered = assignments.filter((item) => assignmentMatches(item, mode, resourceId));
  const periods = [...data.academic_period.periods].sort((a, b) => a.ordinal - b.ordinal);
  const days = [...data.academic_period.days].sort((a, b) => a.ordinal - b.ordinal);
  const locked = new Set(draft?.locked_assignment_ids || []);
  const cells = (day, period) => {
    const lesson = filtered.find((item) => item.slot.day_id === day.id && item.occupied_period_ids.includes(period.id));
    if (!lesson) return "";
    const requirement = data.curriculum_requirements.find((item) => item.id === lesson.requirement_id);
    const subject = data.subjects.find((item) => item.id === requirement?.subject_id)?.label || lesson.requirement_id;
    const teacher = data.teachers.find((item) => item.id === lesson.teacher_id)?.label || lesson.teacher_id;
    const room = data.classrooms.find((item) => item.id === lesson.classroom_id)?.label || lesson.classroom_id;
    const startsHere = lesson.slot.period_id === period.id;
    const classes = `lesson ${draft && startsHere ? "editable" : ""} ${locked.has(lesson.id) ? "locked" : ""}`;
    return `<span class="${classes}" ${draft && startsHere && !locked.has(lesson.id) ? `draggable="true" data-assignment-id="${html(lesson.id)}"` : ""}>${html(subject)}<small>${html(teacher)} · ${html(room)}</small>${draft && startsHere ? `<button type="button" data-edit-assignment="${html(lesson.id)}" aria-label="Edit ${html(subject)}">${locked.has(lesson.id) ? "◆" : "✎"}</button>` : ""}</span>`;
  };
  const timetable = document.querySelector("#timetable");
  timetable.innerHTML = `<table><thead><tr><th>Period</th>${days.map((day) => `<th>${html(day.label)}</th>`).join("")}</tr></thead><tbody>${periods.map((period) => `<tr><th>${html(period.label)}<br><small>${html(period.start_time)}</small></th>${days.map((day) => `<td class="${draft ? "drop-target" : ""}" data-day-id="${html(day.id)}" data-period-id="${html(period.id)}">${cells(day, period)}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
  timetable.querySelectorAll("[data-edit-assignment]").forEach((button) => button.addEventListener("click", () => openMoveDialog(button.dataset.editAssignment)));
  if (draft) bindDragAndDrop(timetable);
}

function updateDraft(draft) {
  const index = state.drafts.findIndex((item) => item.draft_id === draft.draft_id);
  if (index >= 0) state.drafts[index] = draft; else state.drafts.push(draft);
  renderResults();
}

async function createDraft() {
  const job = selectedJob();
  if (!job) return;
  try {
    const draft = await api(`/api/jobs/${job.job_id}/draft`, {method: "POST"});
    updateDraft(draft);
    notice("Editable timetable created");
  } catch (error) { notice(error.message, true); }
}

function openMoveDialog(assignmentId) {
  const draft = selectedDraft();
  const assignment = draft?.version.assignments.find((item) => item.id === assignmentId);
  if (!assignment) return;
  const data = state.dataset.data;
  const fill = (selector, items, selected) => {
    const select = document.querySelector(selector);
    select.innerHTML = items.map((item) => `<option value="${html(item.id)}">${html(item.label)}</option>`).join("");
    select.value = selected;
  };
  document.querySelector("#move-assignment-id").value = assignmentId;
  fill("#move-day", data.academic_period.days, assignment.slot.day_id);
  fill("#move-period", data.academic_period.periods, assignment.slot.period_id);
  fill("#move-teacher", data.teachers, assignment.teacher_id);
  fill("#move-room", data.classrooms, assignment.classroom_id);
  document.querySelector("#toggle-lock").textContent = draft.locked_assignment_ids.includes(assignmentId) ? "Unlock lesson" : "Lock lesson";
  document.querySelector("#move-dialog").showModal();
}

async function moveAssignment(assignmentId, dayId, periodId, teacherId, classroomId) {
  const draft = selectedDraft();
  if (!draft) return;
  try {
    const updated = await api(`/api/drafts/${draft.draft_id}/move`, {
      method: "POST",
      body: JSON.stringify({assignment_id: assignmentId, day_id: dayId, period_id: periodId, teacher_id: teacherId, classroom_id: classroomId})
    });
    updateDraft(updated);
    document.querySelector("#move-dialog").close();
    notice(updated.version.validation_errors.length ? "Move saved with hard conflicts" : "Lesson moved", Boolean(updated.version.validation_errors.length));
  } catch (error) { notice(error.message, true); }
}

async function draftAction(action, payload = {}) {
  const draft = selectedDraft();
  if (!draft) return null;
  const updated = await api(`/api/drafts/${draft.draft_id}/${action}`, {method: "POST", body: JSON.stringify(payload)});
  updateDraft(updated);
  return updated;
}

async function toggleCurrentLock() {
  const draft = selectedDraft();
  const assignmentId = document.querySelector("#move-assignment-id").value;
  if (!draft || !assignmentId) return;
  try {
    const locked = !draft.locked_assignment_ids.includes(assignmentId);
    const updated = await draftAction("lock", {assignment_id: assignmentId, locked});
    document.querySelector("#move-dialog").close();
    notice(locked ? "Lesson locked" : "Lesson unlocked");
    return updated;
  } catch (error) { notice(error.message, true); }
}

async function compareVersions() {
  const draft = selectedDraft();
  if (!draft) return;
  try {
    const comparison = await api(`/api/drafts/${draft.draft_id}/compare`, {
      method: "POST",
      body: JSON.stringify({left: Number(document.querySelector("#compare-left").value), right: Number(document.querySelector("#compare-right").value)})
    });
    const quality = comparison.quality_delta === null ? "quality not comparable" : `quality ${comparison.quality_delta > 0 ? "+" : ""}${comparison.quality_delta}`;
    document.querySelector("#comparison-result").textContent = `${comparison.changes.length} lesson change(s), ${quality}, conflict delta ${comparison.validation_error_delta > 0 ? "+" : ""}${comparison.validation_error_delta}.`;
  } catch (error) { notice(error.message, true); }
}

function bindDragAndDrop(timetable) {
  timetable.querySelectorAll("[draggable=true]").forEach((lesson) => {
    lesson.addEventListener("dragstart", (event) => event.dataTransfer.setData("text/plain", lesson.dataset.assignmentId));
  });
  timetable.querySelectorAll(".drop-target").forEach((cell) => {
    cell.addEventListener("dragover", (event) => { event.preventDefault(); cell.classList.add("drag-over"); });
    cell.addEventListener("dragleave", () => cell.classList.remove("drag-over"));
    cell.addEventListener("drop", async (event) => {
      event.preventDefault();
      cell.classList.remove("drag-over");
      const assignmentId = event.dataTransfer.getData("text/plain");
      const draft = selectedDraft();
      const assignment = draft?.version.assignments.find((item) => item.id === assignmentId);
      if (assignment) await moveAssignment(assignmentId, cell.dataset.dayId, cell.dataset.periodId, assignment.teacher_id, assignment.classroom_id);
    });
  });
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
document.querySelector("#start-editing").addEventListener("click", createDraft);
document.querySelector("#undo-edit").addEventListener("click", async () => { try { await draftAction("undo"); notice("Undid last change"); } catch (error) { notice(error.message, true); } });
document.querySelector("#redo-edit").addEventListener("click", async () => { try { await draftAction("redo"); notice("Redid change"); } catch (error) { notice(error.message, true); } });
document.querySelector("#regenerate-draft").addEventListener("click", async () => { try { notice("Regenerating unlocked lessons…"); await draftAction("regenerate", {time_limit_seconds: 10, seed: 1, workers: 1}); notice("Unlocked lessons regenerated"); } catch (error) { notice(error.message, true); } });
document.querySelector("#compare-versions").addEventListener("click", compareVersions);
document.querySelector("#close-move").addEventListener("click", () => document.querySelector("#move-dialog").close());
document.querySelector("#toggle-lock").addEventListener("click", toggleCurrentLock);
document.querySelector("#move-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  await moveAssignment(
    document.querySelector("#move-assignment-id").value,
    document.querySelector("#move-day").value,
    document.querySelector("#move-period").value,
    document.querySelector("#move-teacher").value,
    document.querySelector("#move-room").value
  );
});
showView(location.hash.slice(1) in titles ? location.hash.slice(1) : "overview");
loadState(true);
