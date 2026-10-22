/* EventCraft planner UI.
   Server strings are written with textContent. The page never builds HTML
   from the brief or from the plan JSON. */

const inr = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});

const PROVIDER_LABELS = {
  spacexai: "SpaceXAI",
  groq: "Groq",
  gemini: "Gemini",
};

const COPY = {
  wedding: {
    host: "Hosts",
    guests: "Guest count",
    guestsHelp: "People you expect to feed.",
    showAge: false,
  },
  birthday: {
    host: "Guest of honour",
    guests: "Guest count",
    guestsHelp: "People you expect at the party.",
    showAge: true,
  },
  community: {
    host: "Organising body",
    guests: "Expected footfall",
    guestsHelp: "The crowd you will actually allow in, not the crowd you hope for.",
    showAge: false,
  },
};

const SAMPLES = {
  wedding: {
    vertical: "wedding",
    event_name: "Meera and Arjun",
    host_names: "Meera Iyer and Arjun Khanna",
    total_budget: 1800000,
    guest_count: 250,
    days_ahead: 240,
    location_tier: "destination",
    city: "Jaipur",
    setting: "outdoor",
    age_group: "",
    vibe: "Modern Rajasthani courtyard wedding",
    cultural_preferences: "Hindu pheras, mehendi, and a short sangeet. The ceremony stays in the courtyard.",
    dietary_notes: "Vegetarian feast with a separate Jain line. No onion and no garlic on the Jain counter.",
    custom_notes: "Keep the baraat short to save transport. A live shehnai for the ceremony, not a DJ.",
    priorities: { venue_catering: 5, decor: 2, photo_video: 3, attire_hospitality: 4, entertainment: 3 },
  },
  "wedding-sprint": {
    vertical: "wedding",
    event_name: "Home ceremony for Nila and Dev",
    host_names: "Nila and Dev",
    total_budget: 450000,
    guest_count: 80,
    days_ahead: 10,
    location_tier: "metro",
    city: "Mumbai",
    setting: "indoor",
    age_group: "",
    vibe: "Short daytime ceremony at home",
    cultural_preferences: "A short Hindu ceremony with close family only.",
    dietary_notes: "Vegetarian lunch.",
    custom_notes: "No procession. Elders need chairs and an early end.",
    priorities: { venue_catering: 5, decor: 1, photo_video: 3, attire_hospitality: 3, entertainment: 2 },
  },
  birthday: {
    vertical: "birthday",
    event_name: "Ananya's 30th",
    host_names: "Ananya Menon",
    total_budget: 150000,
    guest_count: 40,
    days_ahead: 35,
    location_tier: "metro",
    city: "Bengaluru",
    setting: "indoor",
    age_group: "milestone_30",
    vibe: "Retro supper club",
    cultural_preferences: "A family toast before dinner. No religious ceremony.",
    dietary_notes: "A few guests need gluten-free plates.",
    custom_notes: "One seated dinner and one playlist. End by 11.",
    priorities: { venue_catering: 4, entertainment: 4, cake_dessert: 3, decor: 2, photo_video: 3, invites_favors: 2 },
  },
  community: {
    vertical: "community",
    event_name: "Monsoon cultural mela",
    host_names: "Ward 12 residents' committee",
    total_budget: 800000,
    guest_count: 2000,
    days_ahead: 50,
    location_tier: "city",
    city: "Pune",
    setting: "outdoor",
    age_group: "",
    vibe: "Neighbourhood cultural mela with folk performances",
    cultural_preferences: "Local folk sets. Keep the program short enough to end before dark.",
    dietary_notes: "Free drinking water, tea, and a simple vegetarian snack. No alcohol.",
    custom_notes: "Municipal permission is not filed yet. Sponsors can fund safety, not plastic gifts.",
    priorities: { venue_permits: 5, stage_sound: 3, catering: 4, safety: 5, outreach: 2, volunteers: 4 },
  },
};

const PRIORITY_WORDS = { 1: "Low", 2: "Leaning low", 3: "Baseline", 4: "Leaning high", 5: "High" };

let personas = [];
let vertical = "wedding";
let currentPlan = null;
let checks = new Set();
let applying = false;
let checklistFilter = "all";

document.addEventListener("DOMContentLoaded", () => {
  bindStaticControls();
  loadEngineStatus();
  loadPersonas();
});

function bindStaticControls() {
  document.getElementById("planner-form").addEventListener("submit", onSubmit);
  document.getElementById("sample").addEventListener("change", (event) => {
    applySample(event.target.value);
  });
  document.getElementById("copy-plan").addEventListener("click", copySummary);
  document.getElementById("print-plan").addEventListener("click", () => window.print());
  const tablist = document.getElementById("tablist");
  tablist.addEventListener("click", (event) => {
    const tab = event.target.closest('[role="tab"]');
    if (tab) selectTab(tab.dataset.panel);
  });
  tablist.addEventListener("keydown", onTabKeydown);
}

async function loadEngineStatus() {
  const node = document.getElementById("engine-status");
  try {
    const response = await fetch("/health");
    const body = await response.json();
    if (body.llm_configured) {
      const label = PROVIDER_LABELS[body.llm_provider] || body.llm_provider;
      node.textContent = `Rules engine ready. Ideas can also be drafted with ${label}.`;
    } else {
      node.textContent = "Rules engine ready. Add an API key later if you want model-written ideas.";
    }
  } catch (_error) {
    node.textContent = "The planning engine did not answer the health check.";
  }
}

async function loadPersonas() {
  try {
    const response = await fetch("/api/v1/personas");
    if (!response.ok) throw new Error(await readError(response));
    personas = await response.json();
    renderPersonaCards();
    applySample("wedding");
  } catch (error) {
    const node = document.getElementById("persona-error");
    node.hidden = false;
    node.textContent = error.message || "The persona list could not be loaded.";
  }
}

function renderPersonaCards() {
  const group = document.getElementById("persona-group");
  group.replaceChildren();
  personas.forEach((persona, index) => {
    const card = el("button", {
      className: "persona-card",
      attrs: {
        type: "button",
        role: "radio",
        "aria-checked": persona.event_type === vertical ? "true" : "false",
        tabindex: persona.event_type === vertical ? "0" : "-1",
        "data-vertical": persona.event_type,
      },
    });
    const kicker = el("span", { className: "kicker", text: persona.flagship ? "Flagship" : "Vertical" });
    const title = el("strong", { text: persona.name });
    const summary = el("p", { text: persona.summary });
    card.append(kicker, title, summary);
    card.addEventListener("click", () => selectVertical(persona.event_type, true));
    card.addEventListener("keydown", (event) => onPersonaKeydown(event, index));
    group.append(card);
  });
}

function onPersonaKeydown(event, index) {
  const cards = [...document.querySelectorAll(".persona-card")];
  let next = null;
  if (event.key === "ArrowRight" || event.key === "ArrowDown") next = cards[(index + 1) % cards.length];
  if (event.key === "ArrowLeft" || event.key === "ArrowUp") next = cards[(index - 1 + cards.length) % cards.length];
  if (!next) return;
  event.preventDefault();
  selectVertical(next.dataset.vertical, true);
  next.focus();
}

function selectVertical(next, loadSampleIfClean) {
  vertical = next;
  document.body.dataset.vertical = next;
  document.querySelectorAll(".persona-card").forEach((card) => {
    const selected = card.dataset.vertical === next;
    card.setAttribute("aria-checked", selected ? "true" : "false");
    card.tabIndex = selected ? 0 : -1;
  });
  const copy = COPY[next];
  document.getElementById("host-label").textContent = copy.host;
  document.getElementById("guests-label").textContent = `${copy.guests} required`;
  document.getElementById("guests-help").textContent = copy.guestsHelp;
  document.getElementById("age-field").hidden = !copy.showAge;
  renderPriorities(sampleFor(next).priorities);
  if (loadSampleIfClean) {
    const sampleId = next === "wedding" ? "wedding" : next;
    document.getElementById("sample").value = sampleId;
    applySample(sampleId);
  }
}

function sampleFor(name) {
  return SAMPLES[name] || SAMPLES.wedding;
}

function applySample(sampleId) {
  const sample = SAMPLES[sampleId];
  if (!sample) return;
  applying = true;
  hideError();
  if (sample.vertical !== vertical) {
    vertical = sample.vertical;
    document.body.dataset.vertical = vertical;
    document.querySelectorAll(".persona-card").forEach((card) => {
      const selected = card.dataset.vertical === vertical;
      card.setAttribute("aria-checked", selected ? "true" : "false");
      card.tabIndex = selected ? 0 : -1;
    });
    const copy = COPY[vertical];
    document.getElementById("host-label").textContent = copy.host;
    document.getElementById("guests-label").textContent = `${copy.guests} required`;
    document.getElementById("guests-help").textContent = copy.guestsHelp;
    document.getElementById("age-field").hidden = !copy.showAge;
  }
  setValue("event-name", sample.event_name);
  setValue("host-names", sample.host_names);
  setValue("budget", sample.total_budget);
  setValue("guests", sample.guest_count);
  setValue("event-date", isoDaysAhead(sample.days_ahead));
  setValue("city", sample.city);
  setValue("location-tier", sample.location_tier);
  setValue("setting", sample.setting);
  setValue("age-group", sample.age_group);
  setValue("vibe", sample.vibe);
  setValue("culture", sample.cultural_preferences);
  setValue("diet", sample.dietary_notes);
  setValue("notes", sample.custom_notes);
  renderPriorities(sample.priorities);
  applying = false;
  announce(`${sample.event_name} brief loaded. Generate the plan when you are ready.`);
}

function renderPriorities(values) {
  const persona = personas.find((item) => item.event_type === vertical);
  const host = document.getElementById("priority-fields");
  host.replaceChildren();
  if (!persona) return;
  persona.categories.filter((category) => category.adjustable).forEach((category) => {
    const id = `priority-${category.key}`;
    const card = el("div", { className: "priority-card" });
    const label = el("label", { attrs: { for: id }, text: category.label });
    const input = document.createElement("input");
    input.type = "range";
    input.id = id;
    input.min = "1";
    input.max = "5";
    input.step = "1";
    input.value = String(values[category.key] || 3);
    input.dataset.priority = category.key;
    input.setAttribute("aria-describedby", "priority-help");
    const output = el("output", { text: PRIORITY_WORDS[input.value] || "Baseline" });
    output.htmlFor = id;
    input.addEventListener("input", () => {
      output.textContent = PRIORITY_WORDS[input.value] || "Baseline";
    });
    const base = el("p", {
      className: "help",
      text: `Baseline ${category.base_percent}%${category.critical ? ". Protected when you rebalance." : "."}`,
    });
    card.append(label, input, output, base);
    host.append(card);
  });
}

async function onSubmit(event) {
  event.preventDefault();
  const form = event.currentTarget;
  hideError();
  if (!form.reportValidity()) return;
  const button = document.getElementById("generate");
  button.disabled = true;
  button.textContent = "Building the plan";
  button.setAttribute("aria-busy", "true");
  document.getElementById("plan-results").setAttribute("aria-busy", "true");
  try {
    const response = await fetch("/api/v1/plan", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(payloadFromForm()),
    });
    if (!response.ok) throw new Error(await readError(response));
    const plan = await response.json();
    checklistFilter = "all";
    document.getElementById("panel-checklist").dataset.query = "";
    checks = new Set(readStorage(storageKey(plan)));
    renderPlan(plan, true);
    document.getElementById("results-heading").focus();
    announce(`${plan.persona_name} plan ready. ${plan.timeline.days_remaining} days left.`);
  } catch (error) {
    showError(error.message || "The planner could not build that brief.");
  } finally {
    button.disabled = false;
    button.textContent = "Generate plan";
    button.removeAttribute("aria-busy");
    document.getElementById("plan-results").removeAttribute("aria-busy");
  }
}

function payloadFromForm() {
  const priorities = {};
  document.querySelectorAll("[data-priority]").forEach((input) => {
    priorities[input.dataset.priority] = Number(input.value);
  });
  const age = document.getElementById("age-group").value;
  return {
    event_type: vertical,
    event_name: value("event-name"),
    host_names: value("host-names"),
    total_budget: Number(value("budget")),
    guest_count: Number(value("guests")),
    event_date: value("event-date"),
    location_tier: value("location-tier"),
    city: value("city"),
    vibe: value("vibe"),
    cultural_preferences: value("culture"),
    dietary_notes: value("diet"),
    custom_notes: value("notes"),
    priorities,
    age_group: vertical === "birthday" && age ? age : null,
    setting: value("setting"),
  };
}

function renderPlan(plan, resetTab) {
  currentPlan = plan;
  document.getElementById("results-empty").hidden = true;
  document.getElementById("results-body").hidden = false;
  renderSummary(plan);
  document.getElementById("planner-note").textContent = plan.planner_note;
  renderBudget(plan);
  renderTimeline(plan.timeline);
  renderChecklist();
  renderIdeas(plan);
  const assumptions = document.getElementById("assumptions");
  assumptions.replaceChildren();
  plan.assumptions.forEach((item) => assumptions.append(el("li", { text: item })));
  if (resetTab) selectTab("budget");
}

function renderSummary(plan) {
  const mode = plan.timeline.mode.replaceAll("_", " ");
  const decision = plan.decision_mode === "hybrid"
    ? `Rules plus ${PROVIDER_LABELS[plan.provider] || "model"}`
    : "Rules only";
  const summary = document.getElementById("summary");
  summary.replaceChildren(
    stat(plan.event_name, `${plan.city} · ${plan.persona_name}`),
    stat(`${plan.timeline.days_remaining} days`, mode),
    stat(inr.format(plan.budget.per_guest_total), "Per guest, all in"),
    stat(decision, "How this was built"),
  );
}

function stat(primary, label) {
  const wrap = el("div");
  wrap.append(el("span", { className: "label", text: label }), el("strong", { text: primary }));
  return wrap;
}

function renderBudget(plan) {
  const panel = document.getElementById("panel-budget");
  panel.replaceChildren();
  panel.append(el("h3", { text: "Where the money goes" }));
  plan.budget.decision_notes.forEach((note) => panel.append(el("p", { className: "note", text: note })));
  plan.budget.warnings.forEach((warning) => panel.append(el("p", { className: "warning", text: `Warning: ${warning}` })));
  plan.budget.lines.forEach((line) => panel.append(budgetLine(line)));
  panel.append(rebalanceForm(plan));
  const status = el("p", { attrs: { id: "rebalance-status", role: "status" } });
  panel.append(status);
}

function budgetLine(line) {
  const block = el("article", { className: "line" });
  const head = el("div", { className: "line-head" });
  const title = el("h4", { text: line.label });
  const amount = el("p", { className: "meta", text: `${inr.format(line.amount)} · ${line.percent}%` });
  head.append(title, amount);
  const bucket = Math.max(0, Math.min(100, Math.round(line.percent)));
  const meter = el("div", {
    className: "meter",
    attrs: {
      role: "meter",
      "aria-valuemin": "0",
      "aria-valuemax": "100",
      "aria-valuenow": String(bucket),
      "aria-label": `${line.label} is ${line.percent} percent of the budget`,
    },
  });
  meter.append(el("span", { className: `meter-fill p-${bucket}`, attrs: { "aria-hidden": "true" } }));
  const detail = el("p", { className: "meta", text: line.rationale });
  block.append(head, meter, detail);
  const flags = [];
  if (line.critical) flags.push("Protected");
  if (line.per_guest !== null && line.per_guest !== undefined) flags.push(`${inr.format(line.per_guest)} per guest`);
  if (flags.length) block.append(el("p", { className: "meta", text: flags.join(" · ") }));
  return block;
}

function rebalanceForm(plan) {
  const form = el("form", { className: "what-if no-print" });
  const categoryField = el("div", { className: "field" });
  const categoryLabel = el("label", { attrs: { for: "rebalance-category" }, text: "Category to change" });
  const select = el("select", { attrs: { id: "rebalance-category" } });
  plan.budget.lines.forEach((line) => {
    const option = el("option", { text: line.label, attrs: { value: line.key } });
    select.append(option);
  });
  categoryField.append(categoryLabel, select);
  const amountField = el("div", { className: "field" });
  const amountLabel = el("label", { attrs: { for: "rebalance-amount" }, text: "New amount in rupees" });
  const amount = el("input", {
    attrs: { id: "rebalance-amount", type: "number", min: "0", max: String(plan.budget.total_budget), step: "1000", required: "required" },
  });
  amountField.append(amountLabel, amount);
  const button = el("button", { attrs: { type: "submit" }, text: "Rebalance" });
  form.append(categoryField, amountField, button);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!currentPlan) return;
    const allocations = {};
    currentPlan.budget.lines.forEach((line) => {
      allocations[line.key] = line.amount;
    });
    button.disabled = true;
    try {
      const response = await fetch("/api/v1/rebalance-budget", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({
          event_type: currentPlan.event_type,
          total_budget: currentPlan.budget.total_budget,
          guest_count: currentPlan.budget.guest_count,
          location_tier: currentPlan.location_tier,
          allocations,
          changed_category: select.value,
          new_amount: Number(amount.value),
        }),
      });
      if (!response.ok) throw new Error(await readError(response));
      currentPlan.budget = await response.json();
      renderSummary(currentPlan);
      renderBudget(currentPlan);
      announce("Budget rebalanced. The total is unchanged.");
    } catch (error) {
      const status = document.getElementById("rebalance-status");
      if (status) {
        status.className = "alert";
        status.textContent = error.message || "The budget could not be rebalanced.";
      }
    } finally {
      button.disabled = false;
    }
  });
  return form;
}

function renderTimeline(timeline) {
  const panel = document.getElementById("panel-timeline");
  panel.replaceChildren();
  panel.append(el("h3", { text: "Critical path" }));
  panel.append(el("p", { text: timeline.headline }));
  timeline.warnings.forEach((warning) => panel.append(el("p", { className: "warning", text: `Warning: ${warning}` })));
  timeline.phases.forEach((phase) => {
    const section = el("section", { className: "phase" });
    section.append(el("h3", { text: phase }));
    timeline.milestones.filter((item) => item.phase === phase).forEach((item) => {
      const row = el("article", { className: "milestone" });
      const when = el("div");
      when.append(el("p", { className: "status", text: statusLabel(item.status) }), el("p", { className: "meta", text: formatDate(item.due_date) }));
      const body = el("div");
      const title = item.critical ? `${item.title} (critical)` : item.title;
      body.append(el("h4", { text: title }), el("p", { text: item.description }), el("p", { className: "meta", text: `Owner: ${item.owner}` }));
      row.append(when, body);
      section.append(row);
    });
    panel.append(section);
  });
}

function renderChecklist() {
  const plan = currentPlan;
  const panel = document.getElementById("panel-checklist");
  panel.replaceChildren();
  panel.append(el("h3", { text: "Vendor checklist" }));
  panel.append(el("p", { text: plan.checklist.summary }));
  const filters = el("div", { className: "filters no-print" });
  ["all", "critical", "high", "medium", "low"].forEach((name) => {
    const button = el("button", {
      className: "secondary filter",
      attrs: { type: "button", "aria-pressed": checklistFilter === name ? "true" : "false" },
      text: name === "all" ? "All" : name[0].toUpperCase() + name.slice(1),
    });
    button.addEventListener("click", () => {
      checklistFilter = name;
      renderChecklist();
    });
    filters.append(button);
  });
  const searchField = el("div", { className: "field" });
  const searchLabel = el("label", { attrs: { for: "vendor-search" }, text: "Find a vendor" });
  const search = el("input", { attrs: { id: "vendor-search", type: "search" } });
  search.value = panel.dataset.query || "";
  search.addEventListener("input", () => {
    panel.dataset.query = search.value;
    renderChecklist();
    const replacement = document.getElementById("vendor-search");
    if (replacement) {
      replacement.focus();
      replacement.setSelectionRange(replacement.value.length, replacement.value.length);
    }
  });
  searchField.append(searchLabel, search);
  filters.append(searchField);
  panel.append(filters);
  const query = (panel.dataset.query || "").trim().toLowerCase();
  const visible = plan.checklist.items.filter((item) => {
    const priorityOk = checklistFilter === "all" || item.priority === checklistFilter;
    const queryOk = !query || `${item.vendor_role} ${item.notes} ${item.contract_clauses.join(" ")}`.toLowerCase().includes(query);
    return priorityOk && queryOk;
  });
  const done = plan.checklist.items.filter((item) => checks.has(item.id)).length;
  const progress = el("p", { attrs: { role: "status" }, text: `${done} of ${plan.checklist.items.length} marked booked.` });
  panel.append(progress);
  if (!visible.length) panel.append(el("p", { text: "Nothing matches that filter." }));
  visible.forEach((item) => panel.append(checkItem(plan, item)));
}

function checkItem(plan, item) {
  const article = el("article", { className: "check-item" });
  const label = document.createElement("label");
  const box = document.createElement("input");
  box.type = "checkbox";
  box.checked = checks.has(item.id);
  box.addEventListener("change", () => {
    if (box.checked) checks.add(item.id);
    else checks.delete(item.id);
    writeStorage(storageKey(plan), [...checks]);
    const done = plan.checklist.items.filter((row) => checks.has(row.id)).length;
    announce(`${item.vendor_role} ${box.checked ? "marked booked" : "cleared"}. ${done} of ${plan.checklist.items.length} booked.`);
    const status = document.querySelector("#panel-checklist [role='status']");
    if (status) status.textContent = `${done} of ${plan.checklist.items.length} marked booked.`;
  });
  label.append(box, el("span", { text: item.vendor_role }));
  article.append(label);
  article.append(el("p", { className: "meta", text: `${item.priority} · book by ${formatDate(item.book_by)} · typical deposit ${item.deposit_percent}%` }));
  article.append(el("p", { text: item.status_hint }));
  if (item.contract_clauses.length) {
    const list = el("ul");
    item.contract_clauses.forEach((clause) => list.append(el("li", { text: clause })));
    article.append(el("h4", { text: "Contract clauses to watch" }), list);
  }
  article.append(el("p", { className: "meta", text: item.notes }));
  return article;
}

function renderIdeas(plan) {
  const panel = document.getElementById("panel-ideas");
  panel.replaceChildren();
  panel.append(el("h3", { text: "Ideas for this brief" }));
  if (!plan.ideas.length) panel.append(el("p", { text: "No ideas were returned for this brief." }));
  plan.ideas.forEach((idea) => {
    const article = el("article", { className: "idea" });
    const head = el("div", { className: "idea-head" });
    head.append(el("h4", { text: idea.title }), el("p", { className: "meta", text: `${idea.effort} effort` }));
    article.append(head);
    article.append(el("p", { text: idea.summary }));
    article.append(el("p", { text: idea.why_it_fits }));
    article.append(el("p", { text: `Signature: ${idea.signature_experience}` }));
    article.append(el("p", { className: "palette", text: `Palette: ${idea.palette.join(", ")}` }));
    article.append(el("p", { text: `Waste: ${idea.sustainability_tip}` }));
    const source = idea.source === "model" ? "Drafted with the model. Amounts were not." : "From the rule library.";
    article.append(el("p", { className: "meta", text: source }));
    panel.append(article);
  });
  if (plan.sustainability_tips.length) {
    panel.append(el("h3", { text: "Sustainability" }));
    const list = el("ul");
    plan.sustainability_tips.forEach((tip) => list.append(el("li", { text: tip })));
    panel.append(list);
  }
}

function selectTab(name) {
  document.querySelectorAll('[role="tab"]').forEach((tab) => {
    const selected = tab.dataset.panel === name;
    tab.setAttribute("aria-selected", selected ? "true" : "false");
    tab.tabIndex = selected ? 0 : -1;
  });
  document.querySelectorAll('[role="tabpanel"]').forEach((panel) => {
    panel.hidden = panel.id !== `panel-${name}`;
  });
}

function onTabKeydown(event) {
  const tabs = [...document.querySelectorAll('[role="tab"]')];
  const index = tabs.indexOf(document.activeElement);
  if (index < 0) return;
  let next = null;
  if (event.key === "ArrowRight") next = tabs[(index + 1) % tabs.length];
  if (event.key === "ArrowLeft") next = tabs[(index - 1 + tabs.length) % tabs.length];
  if (event.key === "Home") next = tabs[0];
  if (event.key === "End") next = tabs[tabs.length - 1];
  if (!next) return;
  event.preventDefault();
  selectTab(next.dataset.panel);
  next.focus();
}

async function copySummary() {
  if (!currentPlan) return;
  const text = summaryText(currentPlan);
  try {
    await navigator.clipboard.writeText(text);
    announce("Summary copied.");
  } catch (_error) {
    const area = document.createElement("textarea");
    area.value = text;
    document.body.append(area);
    area.select();
    document.execCommand("copy");
    area.remove();
    announce("Summary copied.");
  }
}

function summaryText(plan) {
  const lines = [
    `${plan.event_name} — ${plan.persona_name}`,
    plan.planner_note,
    "",
    "Budget",
  ];
  plan.budget.lines.forEach((line) => {
    lines.push(`- ${line.label}: ${inr.format(line.amount)} (${line.percent}%)`);
  });
  lines.push("", "Timeline", plan.timeline.headline);
  plan.timeline.milestones.forEach((item) => {
    lines.push(`- ${formatDate(item.due_date)} ${item.title} [${statusLabel(item.status)}]`);
  });
  lines.push("", "Vendors");
  plan.checklist.items.forEach((item) => {
    lines.push(`- ${item.vendor_role}: book by ${formatDate(item.book_by)}. ${item.status_hint}`);
  });
  lines.push("", "Ideas");
  plan.ideas.forEach((idea) => lines.push(`- ${idea.title}: ${idea.summary}`));
  return lines.join("\n");
}

function statusLabel(status) {
  return { overdue: "Overdue", due_soon: "Due this week", scheduled: "Scheduled", event_day: "Event day" }[status] || status;
}

function formatDate(iso) {
  const [year, month, day] = iso.split("-").map(Number);
  return new Date(year, month - 1, day).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function isoDaysAhead(days) {
  const date = new Date();
  date.setDate(date.getDate() + days);
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${date.getFullYear()}-${month}-${day}`;
}

function storageKey(plan) {
  return `eventcraft:${plan.event_type}:${plan.event_name}:${plan.timeline.event_date}`;
}

function readStorage(key) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : [];
  } catch (_error) {
    return [];
  }
}

function writeStorage(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch (_error) {
    /* Private mode can refuse storage. The checklist still works for this visit. */
  }
}

async function readError(response) {
  try {
    const body = await response.json();
    const error = body.error || {};
    const details = (error.details || []).join(" ");
    return [error.message || "The planner rejected that brief.", details].filter(Boolean).join(" ");
  } catch (_error) {
    return "The planner rejected that brief.";
  }
}

function showError(message) {
  const node = document.getElementById("form-error");
  node.hidden = false;
  node.textContent = message;
}

function hideError() {
  const node = document.getElementById("form-error");
  node.hidden = true;
  node.textContent = "";
}

function announce(message) {
  const node = document.getElementById("status-announcer");
  node.textContent = "";
  window.setTimeout(() => {
    node.textContent = message;
  }, 30);
}

function setValue(id, content) {
  document.getElementById(id).value = content;
}

function value(id) {
  return document.getElementById(id).value.trim();
}

function el(tag, options = {}) {
  const node = document.createElement(tag);
  if (options.className) node.className = options.className;
  if (options.text != null) node.textContent = options.text;
  if (options.attrs) {
    Object.entries(options.attrs).forEach(([key, attributeValue]) => {
      node.setAttribute(key, attributeValue);
    });
  }
  return node;
}
