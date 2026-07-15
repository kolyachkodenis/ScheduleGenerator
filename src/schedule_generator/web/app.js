const { t, translateStatic, translateError } = window.ScheduleI18n;
const state = { datasets: [], jobs: [], drafts: [], publications: [], permissions: [], currentUser: null, dataset: null, collection: "teachers", selectedTeacherId: null, selectedClassId: null, selectedRoomId: null, poller: null, initialized: false };
const collections = [
  ["teachers", "Teachers"], ["curriculum", "Curriculum"], ["classrooms", "Classrooms"]
];
const titles = { overview: "Overview", data: "School data", rules: "Rules", generate: "Generate", results: "Results", admin: "Security" };
const qualityRules = {
  "SC-001": ["Difficult lessons are concentrated", "The class received more difficulty points in one day than its configured target."],
  "SC-002": ["Uneven daily lesson load", "The number of lessons varies too much between the lightest and busiest day."],
  "SC-003": ["Gaps in a class timetable", "A class has an empty period between its first and last lesson."],
  "SC-004": ["Gaps in a teacher timetable", "A teacher has an empty period between their first and last lesson."],
  "SC-005": ["The same subject repeats in one day", "Several lessons of the same subject were placed on one day instead of being spread across the week."],
  "SC-007": ["Teacher preference was missed", "A lesson starts outside a time marked as preferred by its teacher."],
  "SC-019": ["Related language lessons are on different days", "Language and literature could not be placed on the same day for this class."]
};
const teacherNamesRu = {
  Smirnov: "Смирнов", Kuznetsova: "Кузнецова", Sokolov: "Соколов", Volkova: "Волкова",
  Popov: "Попов", Medvedeva: "Медведева", Ivanov: "Иванов", Morozova: "Морозова",
  Lebedev: "Лебедев", Kovalenko: "Коваленко", Shevchenko: "Шевченко", Bondarenko: "Бондаренко",
  Taylor: "Тейлор", Brown: "Браун", Wilson: "Уилсон", Cooper: "Купер", Harris: "Харрис",
  Orlov: "Орлов", Pavlova: "Павлова", Zaitsev: "Зайцев", Karpov: "Карпов",
  Fedorov: "Фёдоров", Vinogradov: "Виноградов", Mikhailova: "Михайлова", Belyaeva: "Беляева",
  Egorova: "Егорова", Nikolaeva: "Николаева", Alexeev: "Алексеев", Novik: "Новик",
  Kravchenko: "Кравченко", Savchenko: "Савченко", Romanov: "Романов", Semenov: "Семёнов",
  Gromov: "Громов", Kozlova: "Козлова", Sorokina: "Сорокина", Vasiliev: "Васильев",
  Andreev: "Андреев", Tarasov: "Тарасов", Bogdanov: "Богданов", Petrov: "Петров",
  Golubeva: "Голубева", Komarov: "Комаров", Markov: "Марков", Zhukov: "Жуков",
  Kiselev: "Киселёв", Belov: "Белов", Denisov: "Денисов", Martin: "Мартин",
  Kulikov: "Куликов", Fomina: "Фомина"
};

function collectionLabel(key) { return t(collections.find(([item]) => item === key)?.[1] || key); }
function roleLabel(role) { return t(role); }
function statusLabel(status) { return t(status); }
function dataLabel(label) {
  const translated = t(label);
  if (translated !== label || window.ScheduleI18n.language !== "ru") return translated;
  if (teacherNamesRu[label]) return teacherNamesRu[label];
  const section = (value) => ({ A: "А", B: "Б", V: "В" }[value] || value);
  let match = label.match(/^Class (\d+)([ABV])$/);
  if (match) return `${match[1]} «${section(match[2])}» класс`;
  match = label.match(/^Teacher T-(\d+)([ABV])$/);
  if (match) return `Учитель ${match[1]} «${section(match[2])}»`;
  match = label.match(/^Room (\d+)([ABV])$/);
  if (match) return `Кабинет ${match[1]}${section(match[2])}`;
  return translated;
}
function locale() { return window.ScheduleI18n.language === "ru" ? "ru-RU" : "en-US"; }
function formatDate(value) { return new Intl.DateTimeFormat(locale(), {dateStyle: "medium"}).format(new Date(`${value}T00:00:00`)); }
function formatDateTime(value) { return new Intl.DateTimeFormat(locale(), {dateStyle: "short", timeStyle: "short"}).format(new Date(value.endsWith("Z") ? value : `${value}Z`)); }

function can(permission) {
  return state.permissions.includes("*") || state.permissions.includes(permission);
}

function html(value) {
  return String(value).replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character]);
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) }
  });
  const payload = await response.json();
  if (!response.ok) {
    if (response.status === 401 && !path.startsWith("/api/security/")) showAuth(true);
    throw new Error(translateError(payload.detail || payload.error || t("Request failed")));
  }
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
  if (name === "admin" && !can("security:admin")) name = "overview";
  document.querySelectorAll(".view").forEach((view) => view.classList.toggle("active", view.id === `view-${name}`));
  document.querySelectorAll(".nav-item").forEach((item) => item.classList.toggle("active", item.dataset.view === name));
  document.querySelector("#page-title").textContent = t(titles[name]);
  location.hash = name;
  if (name === "results") renderResults();
  if (name === "admin") loadSecurity();
}

function showAuth(initialized) {
  state.initialized = initialized;
  document.querySelector("#auth-gate").hidden = false;
  document.querySelector("#auth-title").textContent = t(initialized ? "Sign in" : "Create administrator");
  document.querySelector("#auth-description").textContent = t(initialized ? "Use your workspace account to continue." : "Initialize this workspace with its first administrator account.");
  document.querySelector("#auth-submit").textContent = t(initialized ? "Sign in" : "Create workspace");
  document.querySelector("#auth-password").autocomplete = initialized ? "current-password" : "new-password";
}

async function initialize() {
  try {
    const status = await api("/api/security/status");
    if (!status.initialized || !status.authenticated) return showAuth(status.initialized);
    document.querySelector("#auth-gate").hidden = true;
    await loadState(true);
  } catch (error) { showAuth(true); }
}

async function authenticate(event) {
  event.preventDefault();
  const error = document.querySelector("#auth-error");
  error.hidden = true;
  try {
    await api(state.initialized ? "/api/security/login" : "/api/security/bootstrap", {
      method: "POST",
      body: JSON.stringify({username: document.querySelector("#auth-username").value, password: document.querySelector("#auth-password").value})
    });
    document.querySelector("#auth-form").reset();
    document.querySelector("#auth-gate").hidden = true;
    await loadState(true);
  } catch (exception) {
    error.textContent = exception.message;
    error.hidden = false;
  }
}

async function loadState(quiet = false) {
  try {
    const payload = await api("/api/state");
    state.datasets = payload.datasets;
    state.jobs = payload.jobs;
    state.drafts = payload.drafts || [];
    state.publications = payload.publications || [];
    state.permissions = payload.permissions || [];
    state.currentUser = payload.current_user || null;
    state.dataset = state.datasets[0] || null;
    render();
    if (!quiet) notice(t("Workspace refreshed"));
  } catch (error) { notice(error.message, true); }
}

function render() {
  const data = state.dataset?.data;
  document.querySelector("#user-badge").textContent = state.currentUser ? `${state.currentUser.username} · ${roleLabel(state.currentUser.role)}` : "";
  document.querySelector("#admin-nav").hidden = !can("security:admin");
  document.querySelector("#load-demo").hidden = !can("data:write");
  document.querySelector("#import-configuration").disabled = !data || !can("data:write");
  document.querySelector("#export-configuration").disabled = !data;
  document.querySelectorAll("#generation-form input, #generation-form button").forEach((element) => { element.disabled = !can("generation:write"); });
  document.querySelector("#empty-state").hidden = Boolean(data);
  document.querySelector("#dashboard").hidden = !data;
  document.querySelector("#dataset-badge").textContent = data ? t("Revision {{revision}} · {{dataset}}", {revision: state.dataset.revision, dataset: data.dataset_id}) : t("No dataset");
  if (!data) return;
  document.querySelector("#school-name").textContent = dataLabel(data.school.label);
  document.querySelector("#period-label").textContent = `${dataLabel(data.academic_period.label)} · ${formatDate(data.academic_period.start_date)} — ${formatDate(data.academic_period.end_date)}`;
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
  document.querySelector("#checklist").innerHTML = items.map(([label, complete]) => `<div class="check-item"><span>${t(label)}</span><b>${t(complete ? "Ready" : "Missing")}</b></div>`).join("");
}

function jobCard(job) {
  return `<div class="job-card ${job.status}"><div><span>${statusLabel(job.status)}</span><span>${job.progress.completed}/${job.progress.total}</span></div><small>${t("Seed {{seed}} · {{seconds}}s per alternative", {seed: job.parameters.seed, seconds: job.parameters.time_limit_seconds})}</small></div>`;
}

function renderJobs() {
  const jobs = [...state.jobs].reverse();
  document.querySelector("#recent-jobs").innerHTML = jobs.length ? jobs.slice(0, 4).map(jobCard).join("") : `<div class="run-placeholder">${t("No jobs yet.")}</div>`;
}

function renderEditor() {
  if (!state.dataset) return;
  const tabs = document.querySelector("#collection-tabs");
  tabs.innerHTML = collections.map(([key]) => `<button class="collection-tab ${key === state.collection ? "active" : ""}" data-collection="${key}">${collectionLabel(key)}</button>`).join("");
  tabs.querySelectorAll("button").forEach((button) => button.addEventListener("click", () => { state.collection = button.dataset.collection; renderEditor(); }));
  const label = collectionLabel(state.collection);
  document.querySelector("#editor-title").textContent = label;
  if (state.collection === "teachers") renderTeachersEditor();
  if (state.collection === "curriculum") renderCurriculumEditor();
  if (state.collection === "classrooms") renderClassroomsEditor();
}

function copyData(value) { return JSON.parse(JSON.stringify(value)); }
function nextId(prefix, records) {
  const used = new Set(records.map((item) => item.id));
  let number = records.length + 1;
  while (used.has(`${prefix}_${number}`)) number += 1;
  return `${prefix}_${number}`;
}
function uniqueId(base, records) {
  const used = new Set(records.map((item) => item.id));
  if (!used.has(base)) return base;
  let number = 2;
  while (used.has(`${base}_${number}`)) number += 1;
  return `${base}_${number}`;
}
function checkedValues(selector) {
  return [...document.querySelectorAll(`${selector}:checked`)].map((item) => item.value);
}
async function saveConfiguration(updates, successMessage) {
  await api(`/api/datasets/${encodeURIComponent(state.dataset.dataset_id)}/configuration`, {
    method: "PUT", body: JSON.stringify({updates})
  });
  await loadState(true);
  notice(t(successMessage));
}

async function exportConfiguration() {
  try {
    const response = await fetch(`/api/datasets/${encodeURIComponent(state.dataset.dataset_id)}/configuration-workbook`);
    if (!response.ok) {
      const payload = await response.json();
      throw new Error(translateError(payload.detail || payload.error || t("Request failed")));
    }
    const disposition = response.headers.get("Content-Disposition") || "";
    const filename = disposition.match(/filename="([^"]+)"/)?.[1] || "school-configuration.xlsx";
    const link = document.createElement("a");
    link.href = URL.createObjectURL(await response.blob());
    link.download = filename;
    link.click();
    URL.revokeObjectURL(link.href);
    notice(t("Configuration exported"));
  } catch (error) { notice(error.message, true); }
}

async function importConfiguration(event) {
  const file = event.target.files?.[0];
  if (!file) return;
  try {
    const content = await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.addEventListener("load", () => resolve(String(reader.result).split(",", 2)[1]));
      reader.addEventListener("error", () => reject(reader.error));
      reader.readAsDataURL(file);
    });
    await api(`/api/datasets/${encodeURIComponent(state.dataset.dataset_id)}/configuration-workbook`, {
      method: "POST", body: JSON.stringify({content_base64: content})
    });
    await loadState(true);
    notice(t("Configuration imported"));
  } catch (error) { notice(error.message, true); }
  finally { event.target.value = ""; }
}

function participantLabel(requirement, data) {
  if (requirement.participant.type === "class") {
    return dataLabel(data.classes.find((item) => item.id === requirement.participant.id)?.label || requirement.participant.id);
  }
  if (requirement.participant.type === "group") {
    return dataLabel(data.groups.find((item) => item.id === requirement.participant.id)?.label || requirement.participant.id);
  }
  return dataLabel(data.cohorts.find((item) => item.id === requirement.participant.id)?.label || requirement.participant.id);
}

function renderTeachersEditor() {
  const data = state.dataset.data;
  const teachers = data.teachers;
  if (!state.selectedTeacherId || (!teachers.some((item) => item.id === state.selectedTeacherId) && state.selectedTeacherId !== "__new__")) {
    state.selectedTeacherId = teachers[0]?.id || "__new__";
  }
  const isNew = state.selectedTeacherId === "__new__";
  const teacher = isNew ? {id: "", label: "", qualified_subject_ids: [], classroom_id: null} : teachers.find((item) => item.id === state.selectedTeacherId);
  const editable = can("data:write");
  const options = teachers.map((item) => `<option value="${html(item.id)}" ${item.id === state.selectedTeacherId ? "selected" : ""}>${html(dataLabel(item.label))}</option>`).join("");
  const subjectChecks = data.subjects.map((subject) => `<label class="choice"><input type="checkbox" data-teacher-subject value="${html(subject.id)}" ${teacher.qualified_subject_ids.includes(subject.id) ? "checked" : ""} ${editable ? "" : "disabled"}><span>${html(dataLabel(subject.label))}</span></label>`).join("");
  const assignmentEntries = data.curriculum_requirements.filter((item) => ["class", "group"].includes(item.participant.type));
  const foreignSubjectIds = new Set(data.subjects.filter((item) => item.id === "english" || item.id.includes("foreign")).map((item) => item.id));
  for (const group of data.groups) {
    for (const subjectId of foreignSubjectIds) {
      const groupRequirement = assignmentEntries.find((item) => item.participant.type === "group" && item.participant.id === group.id && item.subject_id === subjectId);
      const classRequirement = assignmentEntries.find((item) => item.participant.type === "class" && item.participant.id === group.class_id && item.subject_id === subjectId);
      if (!groupRequirement && classRequirement) assignmentEntries.push({...classRequirement, id: `virtual|${group.id}|${subjectId}`, participant: {type: "group", id: group.id}, eligible_teacher_ids: []});
    }
  }
  const assignments = assignmentEntries.map((requirement) => {
    const subject = data.subjects.find((item) => item.id === requirement.subject_id);
    const visible = teacher.qualified_subject_ids.includes(requirement.subject_id);
    const groupClass = requirement.participant.type === "group" ? " subgroup" : "";
    return `<label class="choice assignment-choice${groupClass}" data-assignment-subject="${html(requirement.subject_id)}" ${visible ? "" : "hidden"}><input type="checkbox" data-teacher-requirement value="${html(requirement.id)}" ${requirement.eligible_teacher_ids.includes(teacher.id) ? "checked" : ""} ${editable ? "" : "disabled"}><span>${html(participantLabel(requirement, data))}<small>${html(dataLabel(subject?.label || requirement.subject_id))}${requirement.participant.type === "group" ? ` · ${t("Language subgroup")}` : ""}</small></span></label>`;
  }).join("");
  document.querySelector("#record-count").textContent = t("{{count}} records", {count: teachers.length});
  document.querySelector("#visual-editor").innerHTML = `<div class="editor-selector"><select id="teacher-select" aria-label="${t("Select teacher")}">${options}<option value="__new__" ${isNew ? "selected" : ""}>${t("Add teacher")}</option></select><button id="add-teacher" class="primary-button" ${editable ? "" : "disabled"}>${t("Add teacher")}</button></div><form id="teacher-editor" class="visual-form"><div class="form-grid"><div class="field"><label for="teacher-name">${t("Teacher name")}</label><input id="teacher-name" value="${html(teacher.label)}" required ${editable ? "" : "disabled"}></div><div class="field"><label for="teacher-room">${t("Assigned classroom")}</label><select id="teacher-room" ${editable ? "" : "disabled"}><option value="">${t("No assigned classroom")}</option>${data.classrooms.map((room) => `<option value="${html(room.id)}" ${room.id === teacher.classroom_id ? "selected" : ""}>${html(dataLabel(room.label))}</option>`).join("")}</select></div></div><fieldset><legend>${t("Subjects")}</legend><div class="choice-grid">${subjectChecks}</div></fieldset><fieldset><legend>${t("Classes and language subgroups")}</legend><div class="assignment-list">${assignments || `<p>${t("Create curriculum requirements first.")}</p>`}</div></fieldset><div class="editor-actions"><button id="delete-teacher" type="button" class="danger-button" ${isNew || !editable ? "disabled" : ""}>${t("Delete teacher")}</button><button class="primary-button" type="submit" ${editable ? "" : "disabled"}>${t("Save teacher")}</button></div></form>`;
  document.querySelector("#teacher-select").addEventListener("change", (event) => { state.selectedTeacherId = event.target.value; renderTeachersEditor(); });
  document.querySelector("#add-teacher").addEventListener("click", () => { state.selectedTeacherId = "__new__"; renderTeachersEditor(); });
  document.querySelectorAll("[data-teacher-subject]").forEach((input) => input.addEventListener("change", () => {
    const active = new Set(checkedValues("[data-teacher-subject]"));
    document.querySelectorAll("[data-assignment-subject]").forEach((row) => { row.hidden = !active.has(row.dataset.assignmentSubject); });
  }));
  document.querySelector("#teacher-editor").addEventListener("submit", saveTeacher);
  document.querySelector("#delete-teacher").addEventListener("click", deleteTeacher);
}

async function saveTeacher(event) {
  event.preventDefault();
  try {
    const data = state.dataset.data;
    const teachers = copyData(data.teachers);
    const requirements = copyData(data.curriculum_requirements);
    const isNew = state.selectedTeacherId === "__new__";
    const teacherId = isNew ? nextId("teacher", teachers) : state.selectedTeacherId;
    const qualified = checkedValues("[data-teacher-subject]");
    if (!qualified.length) throw new Error(t("Select at least one subject"));
    const assigned = new Set(checkedValues("[data-teacher-requirement]"));
    const virtualAssignments = [...assigned].filter((id) => id.startsWith("virtual|"));
    for (const virtualId of virtualAssignments) {
      const [, selectedGroupId, subjectId] = virtualId.split("|");
      const selectedGroup = data.groups.find((item) => item.id === selectedGroupId);
      const baseIndex = requirements.findIndex((item) => item.participant.type === "class" && item.participant.id === selectedGroup?.class_id && item.subject_id === subjectId);
      if (!selectedGroup || baseIndex < 0) continue;
      const base = requirements[baseIndex];
      const partitionGroups = data.groups.filter((item) => item.partition_id === selectedGroup.partition_id);
      const created = [];
      for (const group of partitionGroups) {
        let requirement = requirements.find((item) => item.participant.type === "group" && item.participant.id === group.id && item.subject_id === subjectId);
        if (!requirement) {
          requirement = {...copyData(base), id: uniqueId(`req_${group.id}_${subjectId}`, requirements), participant: {type: "group", id: group.id}, allowed_classroom_ids: []};
          requirements.push(requirement);
        }
        created.push(requirement);
      }
      requirements.splice(baseIndex, 1);
      for (const selectedVirtual of virtualAssignments) {
        const [, groupId, selectedSubjectId] = selectedVirtual.split("|");
        if (selectedSubjectId !== subjectId || !partitionGroups.some((item) => item.id === groupId)) continue;
        assigned.delete(selectedVirtual);
        const selectedRequirement = created.find((item) => item.participant.id === groupId);
        if (selectedRequirement) assigned.add(selectedRequirement.id);
      }
    }
    const record = {id: teacherId, label: document.querySelector("#teacher-name").value.trim(), qualified_subject_ids: qualified};
    if (!record.label) throw new Error(t("Teacher name is required"));
    const room = document.querySelector("#teacher-room").value;
    if (room) record.classroom_id = room;
    const index = teachers.findIndex((item) => item.id === teacherId);
    if (index >= 0) teachers[index] = record; else teachers.push(record);
    for (const requirement of requirements) {
      if (!["class", "group"].includes(requirement.participant.type)) {
        if (!qualified.includes(requirement.subject_id)) requirement.eligible_teacher_ids = requirement.eligible_teacher_ids.filter((id) => id !== teacherId);
        continue;
      }
      const eligible = new Set(requirement.eligible_teacher_ids.filter((id) => id !== teacherId));
      if (assigned.has(requirement.id) && qualified.includes(requirement.subject_id)) eligible.add(teacherId);
      requirement.eligible_teacher_ids = [...eligible];
    }
    await saveConfiguration({teachers, curriculum_requirements: requirements}, "Teacher saved");
    state.selectedTeacherId = teacherId;
    renderEditor();
  } catch (error) { notice(error.message, true); }
}

async function deleteTeacher() {
  try {
    const id = state.selectedTeacherId;
    const data = state.dataset.data;
    if (data.fixed_lessons.some((item) => item.teacher_id === id)) throw new Error(t("Move fixed lessons to another teacher before deleting this teacher."));
    const requirements = copyData(data.curriculum_requirements);
    for (const requirement of requirements) requirement.eligible_teacher_ids = requirement.eligible_teacher_ids.filter((item) => item !== id);
    if (requirements.some((item) => !item.eligible_teacher_ids.length)) throw new Error(t("Assign another teacher to every affected lesson before deleting this teacher."));
    const availability = data.resource_availability.filter((item) => !(item.resource.type === "teacher" && item.resource.id === id));
    const policies = copyData(data.policies);
    policies.daily_limits = policies.daily_limits.filter((item) => !(item.resource.type === "teacher" && item.resource.id === id));
    await saveConfiguration({teachers: data.teachers.filter((item) => item.id !== id), curriculum_requirements: requirements, resource_availability: availability, policies}, "Teacher deleted");
    state.selectedTeacherId = null;
    renderEditor();
  } catch (error) { notice(error.message, true); }
}

function renderCurriculumEditor() {
  const data = state.dataset.data;
  if (!state.selectedClassId || !data.classes.some((item) => item.id === state.selectedClassId)) state.selectedClassId = data.classes[0]?.id || null;
  const classItem = data.classes.find((item) => item.id === state.selectedClassId);
  const classGroupIds = new Set(data.groups.filter((item) => item.class_id === state.selectedClassId).map((item) => item.id));
  const requirements = new Map();
  for (const requirement of data.curriculum_requirements) {
    const belongsToClass = requirement.participant.type === "class" && requirement.participant.id === state.selectedClassId;
    const belongsToGroup = requirement.participant.type === "group" && classGroupIds.has(requirement.participant.id);
    if ((belongsToClass || belongsToGroup) && !requirements.has(requirement.subject_id)) requirements.set(requirement.subject_id, requirement);
  }
  const rows = data.subjects.map((subject) => {
    const requirement = requirements.get(subject.id);
    const teacherCount = data.teachers.filter((teacher) => teacher.qualified_subject_ids.includes(subject.id)).length;
    return `<div class="curriculum-row"><div><strong>${html(dataLabel(subject.label))}</strong><small>${t("{{count}} eligible teacher(s)", {count: teacherCount})}</small></div><label><span>${t("Lessons per week")}</span><input type="number" min="0" max="40" value="${requirement?.weekly_lessons || 0}" data-curriculum-subject="${html(subject.id)}" ${can("data:write") ? "" : "disabled"}></label></div>`;
  }).join("");
  document.querySelector("#record-count").textContent = t("{{count}} records", {count: data.classes.length});
  document.querySelector("#visual-editor").innerHTML = `<div class="editor-selector"><label for="curriculum-class">${t("Class")}</label><select id="curriculum-class">${data.classes.map((item) => `<option value="${html(item.id)}" ${item.id === state.selectedClassId ? "selected" : ""}>${html(dataLabel(item.label))}</option>`).join("")}</select></div><form id="curriculum-editor" class="visual-form"><div class="curriculum-list">${rows}</div><div class="editor-actions"><small>${t("Set zero to remove a subject from this class.")}</small><button class="primary-button" type="submit" ${can("data:write") ? "" : "disabled"}>${t("Save curriculum")}</button></div></form>`;
  document.querySelector("#curriculum-class").addEventListener("change", (event) => { state.selectedClassId = event.target.value; renderCurriculumEditor(); });
  document.querySelector("#curriculum-editor").addEventListener("submit", saveCurriculum);
  if (classItem) document.querySelector("#editor-kind").textContent = dataLabel(classItem.label);
}

async function saveCurriculum(event) {
  event.preventDefault();
  try {
    const data = state.dataset.data;
    const requirements = copyData(data.curriculum_requirements);
    const classGroupIds = new Set(data.groups.filter((item) => item.class_id === state.selectedClassId).map((item) => item.id));
    for (const input of document.querySelectorAll("[data-curriculum-subject]")) {
      const subjectId = input.dataset.curriculumSubject;
      const weekly = Number(input.value);
      const index = requirements.findIndex((item) => item.participant.type === "class" && item.participant.id === state.selectedClassId && item.subject_id === subjectId);
      const groupRequirements = requirements.filter((item) => item.participant.type === "group" && classGroupIds.has(item.participant.id) && item.subject_id === subjectId);
      if (weekly === 0) {
        for (let itemIndex = requirements.length - 1; itemIndex >= 0; itemIndex -= 1) {
          const item = requirements[itemIndex];
          const matchesClass = item.participant.type === "class" && item.participant.id === state.selectedClassId;
          const matchesGroup = item.participant.type === "group" && classGroupIds.has(item.participant.id);
          if ((matchesClass || matchesGroup) && item.subject_id === subjectId) requirements.splice(itemIndex, 1);
        }
        continue;
      }
      if (!Number.isInteger(weekly) || weekly < 0 || weekly > 40) throw new Error(t("Weekly lessons must be between 0 and 40."));
      if (index >= 0) { requirements[index].weekly_lessons = weekly; requirements[index].block_length = 1; continue; }
      if (groupRequirements.length) {
        for (const requirement of groupRequirements) { requirement.weekly_lessons = weekly; requirement.block_length = 1; }
        continue;
      }
      const eligible = data.teachers.filter((teacher) => teacher.qualified_subject_ids.includes(subjectId)).map((teacher) => teacher.id);
      if (!eligible.length) {
        const subject = data.subjects.find((item) => item.id === subjectId);
        throw new Error(t("Add a qualified teacher before adding {{subject}}.", {subject: dataLabel(subject?.label || subjectId)}));
      }
      requirements.push({id: uniqueId(`req_${state.selectedClassId.replace(/^class_/, "")}_${subjectId}`, requirements), participant: {type: "class", id: state.selectedClassId}, subject_id: subjectId, eligible_teacher_ids: eligible, weekly_lessons: weekly, block_length: 1, required_room_capabilities: ["general"], allowed_classroom_ids: []});
    }
    await saveConfiguration({curriculum_requirements: requirements}, "Curriculum saved");
    renderEditor();
  } catch (error) { notice(error.message, true); }
}

function renderClassroomsEditor() {
  const data = state.dataset.data;
  if (!state.selectedRoomId || (!data.classrooms.some((item) => item.id === state.selectedRoomId) && state.selectedRoomId !== "__new__")) state.selectedRoomId = data.classrooms[0]?.id || "__new__";
  const isNew = state.selectedRoomId === "__new__";
  const room = isNew ? {id: "", label: "", capacity: 30, capabilities: ["general"]} : data.classrooms.find((item) => item.id === state.selectedRoomId);
  const assignedTeacher = data.teachers.find((item) => item.classroom_id === room.id)?.id || "";
  const capabilities = [...new Set(["general", "sports", "physics_lab", "chemistry_lab", "computer_lab", "workshop", "art", "assembly", ...data.classrooms.flatMap((item) => item.capabilities)])].sort();
  document.querySelector("#record-count").textContent = t("{{count}} records", {count: data.classrooms.length});
  document.querySelector("#visual-editor").innerHTML = `<div class="editor-selector"><select id="room-select" aria-label="${t("Select classroom")}">${data.classrooms.map((item) => `<option value="${html(item.id)}" ${item.id === state.selectedRoomId ? "selected" : ""}>${html(dataLabel(item.label))}</option>`).join("")}<option value="__new__" ${isNew ? "selected" : ""}>${t("Add classroom")}</option></select><button id="add-room" class="primary-button" ${can("data:write") ? "" : "disabled"}>${t("Add classroom")}</button></div><form id="room-editor" class="visual-form"><div class="form-grid"><div class="field"><label for="room-name">${t("Classroom name")}</label><input id="room-name" value="${html(room.label)}" required ${can("data:write") ? "" : "disabled"}></div><div class="field"><label for="room-capacity">${t("Capacity")}</label><input id="room-capacity" type="number" min="1" value="${room.capacity}" required ${can("data:write") ? "" : "disabled"}></div><div class="field"><label for="room-teacher">${t("Assigned teacher")}</label><select id="room-teacher" ${can("data:write") ? "" : "disabled"}><option value="">${t("No assigned teacher")}</option>${data.teachers.map((teacher) => `<option value="${html(teacher.id)}" ${teacher.id === assignedTeacher ? "selected" : ""}>${html(dataLabel(teacher.label))}</option>`).join("")}</select></div></div><fieldset><legend>${t("Room capabilities")}</legend><div class="choice-grid">${capabilities.map((capability) => `<label class="choice"><input type="checkbox" data-room-capability value="${html(capability)}" ${room.capabilities.includes(capability) ? "checked" : ""} ${can("data:write") ? "" : "disabled"}><span>${html(t(capability))}</span></label>`).join("")}</div></fieldset><div class="editor-actions"><button id="delete-room" type="button" class="danger-button" ${isNew || !can("data:write") ? "disabled" : ""}>${t("Delete classroom")}</button><button class="primary-button" type="submit" ${can("data:write") ? "" : "disabled"}>${t("Save classroom")}</button></div></form>`;
  document.querySelector("#room-select").addEventListener("change", (event) => { state.selectedRoomId = event.target.value; renderClassroomsEditor(); });
  document.querySelector("#add-room").addEventListener("click", () => { state.selectedRoomId = "__new__"; renderClassroomsEditor(); });
  document.querySelector("#room-editor").addEventListener("submit", saveClassroom);
  document.querySelector("#delete-room").addEventListener("click", deleteClassroom);
}

async function saveClassroom(event) {
  event.preventDefault();
  try {
    const data = state.dataset.data;
    const rooms = copyData(data.classrooms);
    const teachers = copyData(data.teachers);
    const isNew = state.selectedRoomId === "__new__";
    const roomId = isNew ? nextId("classroom", rooms) : state.selectedRoomId;
    const record = {id: roomId, label: document.querySelector("#room-name").value.trim(), capacity: Number(document.querySelector("#room-capacity").value), capabilities: checkedValues("[data-room-capability]")};
    if (!record.label) throw new Error(t("Classroom name is required"));
    if (!record.capabilities.length) throw new Error(t("Select at least one room capability"));
    const index = rooms.findIndex((item) => item.id === roomId);
    if (index >= 0) rooms[index] = record; else rooms.push(record);
    const teacherId = document.querySelector("#room-teacher").value;
    for (const teacher of teachers) {
      if (teacher.classroom_id === roomId) delete teacher.classroom_id;
      if (teacher.id === teacherId) teacher.classroom_id = roomId;
    }
    await saveConfiguration({classrooms: rooms, teachers}, "Classroom saved");
    state.selectedRoomId = roomId;
    renderEditor();
  } catch (error) { notice(error.message, true); }
}

async function deleteClassroom() {
  try {
    const id = state.selectedRoomId;
    const data = state.dataset.data;
    if (data.classrooms.length <= 1) throw new Error(t("At least one classroom is required."));
    if (data.fixed_lessons.some((item) => item.classroom_id === id)) throw new Error(t("Move fixed lessons out of this classroom before deleting it."));
    const teachers = copyData(data.teachers);
    for (const teacher of teachers) if (teacher.classroom_id === id) delete teacher.classroom_id;
    const requirements = copyData(data.curriculum_requirements);
    for (const requirement of requirements) requirement.allowed_classroom_ids = requirement.allowed_classroom_ids.filter((item) => item !== id);
    const availability = data.resource_availability.filter((item) => !(item.resource.type === "classroom" && item.resource.id === id));
    await saveConfiguration({classrooms: data.classrooms.filter((item) => item.id !== id), teachers, curriculum_requirements: requirements, resource_availability: availability}, "Classroom deleted");
    state.selectedRoomId = null;
    renderEditor();
  } catch (error) { notice(error.message, true); }
}

function renderRules(data) {
  document.querySelector("#difficulty-list").innerHTML = data.subjects.map((subject) => `<label class="form-row difficulty-row"><span><strong>${html(dataLabel(subject.label))}</strong><small>${t("Difficulty affects the daily workload balance")}</small></span><input type="number" min="1" max="5" step="1" value="${subject.default_workload}" data-subject-difficulty="${html(subject.id)}" ${can("data:write") ? "" : "disabled"}></label>`).join("");
  document.querySelector("#difficulty-form button").disabled = !can("data:write");
  document.querySelector("#priority-list").innerHTML = data.policies.soft_constraint_weights.map((rule) => `<div class="form-row"><div><strong>${html(rule.constraint_id)}</strong><small>${html(t(rule.priority))}</small></div><span class="level">${t("Weight {{weight}}", {weight: rule.weight})}</span></div>`).join("");
  const summary = [
    [data.curriculum_requirements.length, "Curriculum rules"],
    [data.resource_availability.length, "Availability records"],
    [data.policies.daily_limits.length, "Daily limits"],
    [data.fixed_lessons.length, "Fixed lessons"]
  ];
  document.querySelector("#rules-summary").innerHTML = summary.map(([value, label]) => `<div><strong>${value}</strong><small>${t(label)}</small></div>`).join("");
}

async function saveDifficulty(event) {
  event.preventDefault();
  try {
    const subjects = copyData(state.dataset.data.subjects);
    for (const input of document.querySelectorAll("[data-subject-difficulty]")) {
      const value = Number(input.value);
      if (!Number.isInteger(value) || value < 1 || value > 5) throw new Error(t("Difficulty must be between 1 and 5."));
      subjects.find((item) => item.id === input.dataset.subjectDifficulty).default_workload = value;
    }
    await saveConfiguration({subjects}, "Difficulty saved");
  } catch (error) { notice(error.message, true); }
}

function renderCurrentRun() {
  const job = [...state.jobs].reverse().find((item) => ["PENDING", "RUNNING"].includes(item.status)) || [...state.jobs].reverse()[0];
  const target = document.querySelector("#current-run");
  if (!job) { target.innerHTML = `<div class="run-placeholder">${t("No generation job is active.")}</div>`; return; }
  const progress = Math.round(job.progress.completed / Math.max(1, job.progress.total) * 100);
  target.innerHTML = `<div class="run-status"><div><p class="eyebrow">${statusLabel(job.status)}</p><h3>${t(job.status === "SUCCEEDED" ? "Timetable ready" : job.status === "RUNNING" ? "Building alternatives" : "Generation job")}</h3></div><div class="progress-track"><div class="progress-fill" style="width:${progress}%"></div></div><div class="run-meta"><div><small>${t("Progress")}</small><strong>${t("{{complete}} of {{total}}", {complete: job.progress.completed, total: job.progress.total})}</strong></div><div><small>${t("Seed")}</small><strong>${job.parameters.seed}</strong></div><div><small>${t("Limit")}</small><strong>${job.parameters.time_limit_seconds} ${t("seconds")}</strong></div></div>${["PENDING", "RUNNING"].includes(job.status) ? `<button id="cancel-job" class="text-button">${t("Cancel generation")}</button>` : `<button class="primary-button" data-go="results">${t("Review result")}</button>`}</div>`;
  target.querySelector("#cancel-job")?.addEventListener("click", () => cancelJob(job.job_id));
  target.querySelector("[data-go]")?.addEventListener("click", () => showView("results"));
  if (["PENDING", "RUNNING"].includes(job.status)) startPolling(); else stopPolling();
}

function renderJobSelect() {
  const select = document.querySelector("#job-select");
  const successful = [...state.jobs].reverse().filter((job) =>
    job.status === "SUCCEEDED" && job.dataset_revision === state.dataset?.revision
  );
  const previous = select.value;
  select.innerHTML = successful.length ? successful.map((job) => `<option value="${job.job_id}">${job.job_id.slice(0, 8)} · ${t("{{count}} alternative(s)", {count: job.parameters.alternatives})}</option>`).join("") : `<option value="">${t("No successful jobs")}</option>`;
  if (successful.some((job) => job.job_id === previous)) select.value = previous;
}

function selectedJob() {
  const id = document.querySelector("#job-select").value;
  return state.jobs.find((job) => job.job_id === id && job.dataset_revision === state.dataset?.revision)
    || [...state.jobs].reverse().find((job) => job.status === "SUCCEEDED" && job.dataset_revision === state.dataset?.revision);
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
  document.querySelector("#quality-chip").textContent = report ? t("Quality penalty {{penalty}}", {penalty: report.total_penalty}) : t("Feasible timetable");
  const violations = report?.violations || [];
  const grouped = Object.entries(report?.by_constraint || {}).sort((left, right) => right[1].weighted - left[1].weighted);
  document.querySelector("#quality-report").innerHTML = grouped.length ? grouped.map(([constraintId, values]) => {
    const [title, explanation] = qualityRules[constraintId] || [constraintId, "This configured preference could not be fully met."];
    const count = violations.filter((item) => item.constraint_id === constraintId).length;
    return `<div class="quality-item"><strong>${html(t(title))}</strong><small>${t("{{count}} case(s) · {{points}} penalty point(s)", {count, points: values.weighted})}</small><p>${html(t(explanation))}</p></div>`;
  }).join("") : `<div class="check-item"><span>${t("No preference violations")}</span><b>${t("Excellent")}</b></div>`;
  renderEditing(draft);
  renderPublication(draft);
  renderResourceOptions();
  renderTimetable(result.assignments, draft);
}

function changeLabel(change) {
  if (change.type === "generated") return t("Generated result");
  if (change.type === "move") return t("Moved {{assignment}}", {assignment: change.assignment_id});
  if (change.type === "regenerate") return t("Regenerated with {{count}} lock(s)", {count: change.locked_assignment_ids.length});
  return t(change.type);
}

function renderEditing(draft) {
  const start = document.querySelector("#start-editing");
  const undo = document.querySelector("#undo-edit");
  const redo = document.querySelector("#redo-edit");
  const regenerate = document.querySelector("#regenerate-draft");
  const historyPanel = document.querySelector("#history-panel");
  const conflict = document.querySelector("#conflict-banner");
  const editable = can("draft:write");
  start.hidden = Boolean(draft) || !editable;
  undo.disabled = !editable || !draft || draft.current_version === 0;
  redo.disabled = !editable || !draft || draft.current_version >= draft.latest_version;
  regenerate.hidden = !editable || !draft;
  historyPanel.hidden = !draft;
  document.querySelector("#version-label").textContent = draft ? t("Draft version {{version}}", {version: draft.current_version}) : t("Generated result");
  const errors = draft?.version.validation_errors || [];
  conflict.hidden = !errors.length;
  conflict.textContent = errors.length ? t("{{count}} hard conflict(s): {{errors}}", {count: errors.length, errors: errors.map(translateError).join(" · ")}) : "";
  if (!draft) return;
  document.querySelector("#version-history").innerHTML = [...draft.history].reverse().map((item) => `<div class="version-item ${item.version === draft.current_version ? "current" : ""}"><strong>${t("Version {{version}}", {version: item.version})}</strong><small>${html(changeLabel(item.change))}</small></div>`).join("");
  const options = draft.history.map((item) => `<option value="${item.version}">${t("Version {{version}}", {version: item.version})}</option>`).join("");
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
    target.innerHTML = `<p>${t("Create an editable timetable before approval.")}</p>`;
    return;
  }
  const publication = state.publications.find((item) => item.draft_id === draft.draft_id && item.version === draft.current_version);
  if (!publication) {
    const blocked = draft.version.validation_errors.length > 0;
    const action = can("publication:write") ? `<button id="approve-publication" class="primary-button" ${blocked ? "disabled" : ""}>${t("Approve version")}</button>` : "";
    target.innerHTML = `<p>${t(blocked ? "Version {{version}} is a draft with unresolved conflicts." : "Version {{version}} is a draft ready for review.", {version: draft.current_version})}</p>${action}`;
    target.querySelector("#approve-publication")?.addEventListener("click", approvePublication);
    return;
  }
  if (publication.status === "APPROVED") {
    const action = can("publication:write") ? `<button id="publish-publication" class="primary-button">${t("Publish XLSX and PDF")}</button>` : "";
    target.innerHTML = `<p><span class="status-pill approved">${t("Approved")}</span> ${t("Version {{version}} is immutable and ready to publish.", {version: publication.version})}</p>${action}`;
    target.querySelector("#publish-publication")?.addEventListener("click", () => changePublication(publication.publication_id, "publish"));
    return;
  }
  const links = Object.entries(publication.artifacts).map(([kind, artifact]) => `<a href="/downloads/${encodeURIComponent(artifact.filename)}">${t("Download {{kind}}", {kind: html(kind.toUpperCase())})}</a>`).join("");
  if (publication.status === "PUBLISHED") {
    const action = can("publication:write") ? `<button id="unpublish-publication" class="text-button">${t("Unpublish")}</button>` : "";
    target.innerHTML = `<p><span class="status-pill published">${t("Published")}</span> ${t("Version {{version}} is available for distribution.", {version: publication.version})}</p><div class="download-links">${links}</div>${action}`;
    target.querySelector("#unpublish-publication")?.addEventListener("click", () => changePublication(publication.publication_id, "unpublish"));
  } else {
    const action = can("publication:write") ? `<button id="republish-publication" class="primary-button">${t("Publish again")}</button>` : "";
    target.innerHTML = `<p><span class="status-pill unpublished">${t("Unpublished")}</span> ${t("Version {{version}} is no longer available for download.", {version: publication.version})}</p>${action}`;
    target.querySelector("#republish-publication")?.addEventListener("click", () => changePublication(publication.publication_id, "publish"));
  }
}

async function approvePublication() {
  const draft = selectedDraft();
  if (!draft) return;
  try {
    await api(`/api/drafts/${draft.draft_id}/approve`, {method: "POST"});
    await loadState(true);
    notice(t("Version {{version}} approved", {version: draft.current_version}));
  } catch (error) { notice(error.message, true); }
}

async function changePublication(publicationId, action) {
  try {
    await api(`/api/publications/${publicationId}/${action}`, {method: "POST"});
    await loadState(true);
    notice(t(action === "publish" ? "Timetable published" : "Timetable unpublished"));
  } catch (error) { notice(error.message, true); }
}

function renderResourceOptions() {
  const mode = document.querySelector("#view-mode").value;
  const data = state.dataset.data;
  const resources = mode === "class" ? data.classes : mode === "teacher" ? data.teachers : data.classrooms;
  const select = document.querySelector("#resource-select");
  const previous = select.value;
  select.innerHTML = resources.map((item) => `<option value="${html(item.id)}">${html(dataLabel(item.label))}</option>`).join("");
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
  const cells = (day, period) => filtered
    .filter((item) => item.slot.day_id === day.id && item.occupied_period_ids.includes(period.id))
    .map((lesson) => {
      const requirement = data.curriculum_requirements.find((item) => item.id === lesson.requirement_id);
      const subject = dataLabel(data.subjects.find((item) => item.id === requirement?.subject_id)?.label || lesson.requirement_id);
      const teacher = dataLabel(data.teachers.find((item) => item.id === lesson.teacher_id)?.label || lesson.teacher_id);
      const room = dataLabel(data.classrooms.find((item) => item.id === lesson.classroom_id)?.label || lesson.classroom_id);
      const group = requirement?.participant.type === "group" ? dataLabel(data.groups.find((item) => item.id === requirement.participant.id)?.label || requirement.participant.id) : "";
      const startsHere = lesson.slot.period_id === period.id;
      const classes = `lesson ${draft && startsHere ? "editable" : ""} ${locked.has(lesson.id) ? "locked" : ""}`;
      return `<span class="${classes}" ${draft && startsHere && !locked.has(lesson.id) ? `draggable="true" data-assignment-id="${html(lesson.id)}"` : ""}>${html(subject)}${group ? `<em>${html(group)}</em>` : ""}<small>${html(teacher)} · ${html(room)}</small>${draft && startsHere ? `<button type="button" data-edit-assignment="${html(lesson.id)}" aria-label="${t("Edit {{subject}}", {subject: html(subject)})}">${locked.has(lesson.id) ? "◆" : "✎"}</button>` : ""}</span>`;
    }).join("");
  const timetable = document.querySelector("#timetable");
  timetable.innerHTML = `<table><thead><tr><th>${t("Period")}</th>${days.map((day) => `<th>${html(dataLabel(day.label))}</th>`).join("")}</tr></thead><tbody>${periods.map((period) => `<tr><th>${html(dataLabel(period.label))}<br><small>${html(period.start_time)}</small></th>${days.map((day) => `<td class="${draft ? "drop-target" : ""}" data-day-id="${html(day.id)}" data-period-id="${html(period.id)}">${cells(day, period)}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
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
    notice(t("Editable timetable created"));
  } catch (error) { notice(error.message, true); }
}

function openMoveDialog(assignmentId) {
  const draft = selectedDraft();
  const assignment = draft?.version.assignments.find((item) => item.id === assignmentId);
  if (!assignment) return;
  const data = state.dataset.data;
  const fill = (selector, items, selected) => {
    const select = document.querySelector(selector);
    select.innerHTML = items.map((item) => `<option value="${html(item.id)}">${html(dataLabel(item.label))}</option>`).join("");
    select.value = selected;
  };
  document.querySelector("#move-assignment-id").value = assignmentId;
  fill("#move-day", data.academic_period.days, assignment.slot.day_id);
  fill("#move-period", data.academic_period.periods, assignment.slot.period_id);
  fill("#move-teacher", data.teachers, assignment.teacher_id);
  fill("#move-room", data.classrooms, assignment.classroom_id);
  document.querySelector("#toggle-lock").textContent = t(draft.locked_assignment_ids.includes(assignmentId) ? "Unlock lesson" : "Lock lesson");
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
    notice(t(updated.version.validation_errors.length ? "Move saved with hard conflicts" : "Lesson moved"), Boolean(updated.version.validation_errors.length));
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
    notice(t(locked ? "Lesson locked" : "Lesson unlocked"));
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
    const quality = comparison.quality_delta === null ? t("quality not comparable") : t("quality {{delta}}", {delta: `${comparison.quality_delta > 0 ? "+" : ""}${comparison.quality_delta}`});
    document.querySelector("#comparison-result").textContent = t("{{count}} lesson change(s), {{quality}}, conflict delta {{delta}}.", {count: comparison.changes.length, quality, delta: `${comparison.validation_error_delta > 0 ? "+" : ""}${comparison.validation_error_delta}`});
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

async function startGeneration(event) {
  event.preventDefault();
  if (!state.dataset) return notice(t("Load school data first"), true);
  try {
    const job = await api("/api/jobs", { method: "POST", body: JSON.stringify({
      dataset_id: state.dataset.dataset_id,
      alternatives: Number(document.querySelector("#alternatives").value),
      time_limit_seconds: Number(document.querySelector("#time-limit").value),
      seed: Number(document.querySelector("#seed").value), workers: 1
    }) });
    notice(t("Generation job {{job}} started", {job: job.job_id.slice(0, 8)}));
    await loadState(true);
    startPolling();
  } catch (error) { notice(error.message, true); }
}

async function cancelJob(jobId) {
  try { await api(`/api/jobs/${jobId}/cancel`, { method: "POST" }); await loadState(true); notice(t("Cancellation requested")); }
  catch (error) { notice(error.message, true); }
}

async function loadSecurity() {
  if (!can("security:admin")) return;
  try {
    const [users, audit] = await Promise.all([api("/api/users"), api("/api/audit")]);
    document.querySelector("#user-list").innerHTML = users.users.map((user) => `<div class="user-row ${user.enabled ? "" : "disabled"}" data-user-id="${html(user.user_id)}"><div><strong>${html(user.username)}</strong><small>${t(user.enabled ? "Enabled" : "Disabled")}</small></div><select data-user-role>${["administrator", "scheduler", "reviewer", "reader"].map((role) => `<option value="${role}" ${role === user.role ? "selected" : ""}>${roleLabel(role)}</option>`).join("")}</select><button class="text-button" data-toggle-user data-enable="${String(!user.enabled)}">${t(user.enabled ? "Disable" : "Enable")}</button></div>`).join("");
    document.querySelectorAll("[data-user-role]").forEach((select) => select.addEventListener("change", () => updateUser(select.closest("[data-user-id]").dataset.userId, {role: select.value})));
    document.querySelectorAll("[data-toggle-user]").forEach((button) => button.addEventListener("click", () => updateUser(button.closest("[data-user-id]").dataset.userId, {enabled: button.dataset.enable === "true"})));
    document.querySelector("#audit-list").innerHTML = audit.events.length ? audit.events.map((event) => `<div class="audit-row ${html(event.outcome)}"><strong>${html(t(event.action))}</strong><small>${html(event.actor_username || t("system"))} · ${html(t(event.target_type))}${event.target_id ? ` · ${html(event.target_id)}` : ""} · ${html(formatDateTime(event.created_at))}</small></div>`).join("") : `<div class="run-placeholder">${t("No audit events.")}</div>`;
  } catch (error) { notice(error.message, true); }
}

async function createUser(event) {
  event.preventDefault();
  try {
    await api("/api/users", {method: "POST", body: JSON.stringify({username: document.querySelector("#new-username").value, role: document.querySelector("#new-role").value, password: document.querySelector("#new-password").value})});
    event.target.reset();
    await loadSecurity();
    notice(t("User created"));
  } catch (error) { notice(error.message, true); }
}

async function updateUser(userId, changes) {
  try {
    await api(`/api/users/${encodeURIComponent(userId)}`, {method: "PUT", body: JSON.stringify(changes)});
    await loadSecurity();
    notice(t("User updated"));
  } catch (error) { await loadSecurity(); notice(error.message, true); }
}

async function createBackup() {
  try {
    const backup = await api("/api/admin/backup", {method: "POST"});
    await loadSecurity();
    notice(t("Backup {{filename}} created", {filename: backup.filename}));
  } catch (error) { notice(error.message, true); }
}

async function logout() {
  try { await api("/api/security/logout", {method: "POST"}); } catch (_error) { /* Session may already be gone. */ }
  state.currentUser = null;
  state.permissions = [];
  showAuth(true);
}

function startPolling() {
  if (state.poller) return;
  state.poller = setInterval(() => loadState(true), 1200);
}
function stopPolling() { clearInterval(state.poller); state.poller = null; }

document.querySelectorAll(".nav-item").forEach((item) => item.addEventListener("click", () => showView(item.dataset.view)));
document.querySelectorAll("[data-go]").forEach((item) => item.addEventListener("click", () => showView(item.dataset.go)));
document.querySelector("#refresh").addEventListener("click", () => loadState());
document.querySelector("#auth-form").addEventListener("submit", authenticate);
document.querySelector("#logout").addEventListener("click", logout);
document.querySelector("#load-demo").addEventListener("click", async () => { try { await api("/api/demo", { method: "POST" }); await loadState(true); notice(t("Demonstration school loaded")); } catch (error) { notice(error.message, true); } });
document.querySelector("#export-configuration").addEventListener("click", exportConfiguration);
document.querySelector("#import-configuration").addEventListener("click", () => document.querySelector("#configuration-file").click());
document.querySelector("#configuration-file").addEventListener("change", importConfiguration);
document.querySelector("#generation-form").addEventListener("submit", startGeneration);
document.querySelector("#difficulty-form").addEventListener("submit", saveDifficulty);
document.querySelector("#job-select").addEventListener("change", renderResults);
document.querySelector("#view-mode").addEventListener("change", () => { renderResourceOptions(); renderResults(); });
document.querySelector("#resource-select").addEventListener("change", renderResults);
document.querySelector("#start-editing").addEventListener("click", createDraft);
document.querySelector("#undo-edit").addEventListener("click", async () => { try { await draftAction("undo"); notice(t("Undid last change")); } catch (error) { notice(error.message, true); } });
document.querySelector("#redo-edit").addEventListener("click", async () => { try { await draftAction("redo"); notice(t("Redid change")); } catch (error) { notice(error.message, true); } });
document.querySelector("#regenerate-draft").addEventListener("click", async () => { try { notice(t("Regenerating unlocked lessons…")); await draftAction("regenerate", {time_limit_seconds: 10, seed: 1, workers: 1}); notice(t("Unlocked lessons regenerated")); } catch (error) { notice(error.message, true); } });
document.querySelector("#compare-versions").addEventListener("click", compareVersions);
document.querySelector("#user-form").addEventListener("submit", createUser);
document.querySelector("#refresh-security").addEventListener("click", loadSecurity);
document.querySelector("#create-backup").addEventListener("click", createBackup);
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
window.addEventListener("schedule-language-change", () => {
  translateStatic();
  if (!document.querySelector("#auth-gate").hidden) showAuth(state.initialized);
  render();
  showView(location.hash.slice(1) in titles ? location.hash.slice(1) : "overview");
});
showView(location.hash.slice(1) in titles ? location.hash.slice(1) : "overview");
initialize();
