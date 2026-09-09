// Builder page: drives the real discover -> analyze -> design-tools -> generate -> validate
// pipeline. Every stage transition is tied to an actual fetch's lifecycle (start/resolve/reject) —
// never a timer.
(() => {
  "use strict";

  const RECENT_KEY = "mcp-builder:recent-urls";
  const EXAMPLE_URL = "https://petstore3.swagger.io/api/v3/openapi.json";
  const MAX_RECENT = 5;

  const STAGES = [
    { id: "connect", label: "Connecting to URL", phase: "discover" },
    { id: "inspect", label: "Inspecting documentation", phase: "discover" },
    { id: "detect", label: "Detecting API specification", phase: "discover" },
    { id: "parse", label: "Parsing endpoints", phase: "analyze" },
    { id: "auth", label: "Understanding authentication", phase: "analyze" },
    { id: "design", label: "Designing MCP tools", phase: "design" },
    { id: "generate", label: "Generating server", phase: "generate" },
    { id: "validate", label: "Validating implementation", phase: "validate" },
  ];

  const state = {
    projectId: null,
    discovery: null,
    api: null,
    design: null,
    generated: null,
    validation: null,
    files: [],
    endpoints: [],
    methodFilter: null,
    selectedToolNames: new Set(),
    lastSelectedToolNames: [],
    isGenerated: false,
    currentFile: null,
    fileSearch: "",
    fileTreeRows: null,
    rating: 0,
  };

  // ---------- generic helpers ----------

  function esc(str) {
    return String(str ?? "").replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
  }

  function showEl(el) { if (el) el.hidden = false; }
  function hideEl(el) { if (el) el.hidden = true; }

  function isPlausibleUrl(value) {
    if (!value) return false;
    try {
      const parsed = new URL(value);
      return parsed.protocol === "http:" || parsed.protocol === "https:";
    } catch {
      return false;
    }
  }

  function methodBadgeClass(method) {
    const map = {
      GET: "badge-method-get", POST: "badge-method-post", PUT: "badge-method-put",
      PATCH: "badge-method-patch", DELETE: "badge-method-delete",
    };
    return map[method] || "badge-neutral";
  }

  function authLabel(type) {
    const map = { api_key: "API Key", bearer: "Bearer Token", basic: "Basic Auth", oauth2: "OAuth 2.0", none: "None", unknown: "Unknown" };
    return map[type] || type || "Unknown";
  }

  async function apiPost(path, body) {
    const res = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
    });
    let data = null;
    try { data = await res.json(); } catch { /* no body */ }
    if (!res.ok) throw new Error((data && data.detail) || `Request failed (${res.status})`);
    return data;
  }

  async function apiGet(path) {
    const res = await fetch(path);
    let data = null;
    try { data = await res.json(); } catch { /* no body */ }
    if (!res.ok) throw new Error((data && data.detail) || `Request failed (${res.status})`);
    return data;
  }

  // ---------- toasts ----------

  function showToast(message, tone) {
    const container = document.getElementById("toast-container");
    if (!container) return;
    const el = document.createElement("div");
    el.className = "toast";
    el.setAttribute("data-tone", tone || "default");
    el.setAttribute("role", tone === "error" ? "alert" : "status");
    const text = document.createElement("span");
    text.className = "min-w-0 flex-1";
    text.textContent = message;
    el.appendChild(text);
    container.appendChild(el);
    setTimeout(() => {
      el.classList.add("toast-leaving");
      el.addEventListener("animationend", () => el.remove(), { once: true });
      setTimeout(() => el.remove(), 400);
    }, 4000);
  }

  // ---------- confirm dialog ----------

  function showConfirm(title, message, onConfirm) {
    const dialog = document.getElementById("confirm-dialog");
    if (!dialog) { onConfirm(); return; }
    document.getElementById("confirm-title").textContent = title;
    document.getElementById("confirm-message").textContent = message;
    dialog.hidden = false;
    const okBtn = document.getElementById("confirm-ok");
    const cancelBtn = document.getElementById("confirm-cancel");
    function cleanup() {
      dialog.hidden = true;
      okBtn.removeEventListener("click", onOk);
      cancelBtn.removeEventListener("click", onCancel);
    }
    function onOk() { cleanup(); onConfirm(); }
    function onCancel() { cleanup(); }
    okBtn.addEventListener("click", onOk);
    cancelBtn.addEventListener("click", onCancel);
    okBtn.focus();
  }

  document.addEventListener("DOMContentLoaded", () => {
    const dialog = document.getElementById("confirm-dialog");
    dialog?.addEventListener("click", (e) => {
      if (e.target === dialog) document.getElementById("confirm-cancel")?.click();
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && dialog && !dialog.hidden) document.getElementById("confirm-cancel")?.click();
    });
  });

  // ---------- recent urls ----------

  function readRecentUrls() {
    try {
      const raw = localStorage.getItem(RECENT_KEY);
      const list = raw ? JSON.parse(raw) : [];
      return Array.isArray(list) ? list : [];
    } catch { return []; }
  }

  function pushRecentUrl(url) {
    const list = readRecentUrls().filter((u) => u !== url);
    list.unshift(url);
    try { localStorage.setItem(RECENT_KEY, JSON.stringify(list.slice(0, MAX_RECENT))); } catch { /* ignore */ }
  }

  function renderBuilderRecentUrls() {
    const wrap = document.getElementById("builder-recent-urls");
    const list = document.getElementById("builder-recent-urls-list");
    if (!wrap || !list) return;
    const urls = readRecentUrls();
    if (!urls.length) { wrap.classList.add("hidden"); return; }
    wrap.classList.remove("hidden");
    list.innerHTML = "";
    urls.forEach((url) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "max-w-[16rem] truncate rounded-full border border-line bg-surface px-3 py-1.5 font-mono text-xs text-ink-secondary hover:border-line-strong hover:text-ink";
      btn.textContent = url;
      btn.title = url;
      btn.addEventListener("click", () => {
        const input = document.getElementById("builder-url");
        if (input) { input.value = url; input.focus(); }
      });
      list.appendChild(btn);
    });
  }

  // ---------- stage tracker ----------

  function renderStageList() {
    const list = document.getElementById("stage-list");
    if (!list) return;
    list.innerHTML = "";
    STAGES.forEach((s) => {
      const li = document.createElement("li");
      li.className = "stage-item";
      li.dataset.stage = s.id;
      li.dataset.state = "waiting";
      const dot = document.createElement("span");
      dot.className = "stage-dot";
      dot.setAttribute("aria-hidden", "true");
      const label = document.createElement("span");
      label.className = "stage-label text-sm";
      label.textContent = s.label;
      li.appendChild(dot);
      li.appendChild(label);
      list.appendChild(li);
    });
  }

  const ICON_CHECK = '<svg class="stage-check" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M5 13l4 4L19 7"/></svg>';
  const ICON_X = '<svg class="stage-x" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M6 6l12 12M18 6L6 18"/></svg>';

  function setStage(id, uiState) {
    const li = document.querySelector(`#stage-list [data-stage="${id}"]`);
    if (!li) return;
    li.dataset.state = uiState;
    const dot = li.querySelector(".stage-dot");
    if (dot) {
      if (uiState === "running") dot.innerHTML = '<span class="stage-spinner" aria-hidden="true"></span>';
      else if (uiState === "done") dot.innerHTML = ICON_CHECK;
      else if (uiState === "failed") dot.innerHTML = ICON_X;
      else dot.innerHTML = "";
    }
    const stage = STAGES.find((s) => s.id === id);
    const announcer = document.getElementById("stage-announcer");
    if (stage && announcer && uiState !== "waiting") announcer.textContent = `${stage.label}: ${uiState}`;
  }

  function setPhase(phase, uiState) {
    STAGES.filter((s) => s.phase === phase).forEach((s) => setStage(s.id, uiState));
  }

  async function runPhase(phase, fn) {
    setPhase(phase, "running");
    const result = await fn();
    setPhase(phase, "done");
    return result;
  }

  // ---------- pipeline ----------

  function resetPipelineUI() {
    state.projectId = null;
    state.discovery = null;
    state.api = null;
    state.design = null;
    state.generated = null;
    state.validation = null;
    state.files = [];
    state.endpoints = [];
    state.methodFilter = null;
    state.selectedToolNames = new Set();
    state.lastSelectedToolNames = [];
    state.isGenerated = false;
    state.currentFile = null;
    document.getElementById("stage-failure").hidden = true;
    hideEl(document.getElementById("discovery-section"));
    hideEl(document.getElementById("tools-section"));
    hideEl(document.getElementById("result-section"));
    document.getElementById("result-section").innerHTML = "";
    renderStageList();
  }

  async function startPipeline(url, demo) {
    resetPipelineUI();
    showEl(document.getElementById("stage-section"));
    document.getElementById("stage-source").textContent = demo ? "Demo mode — Task Manager API" : url;
    setBuilderFormBusy(true);
    try {
      await runPhase("discover", async () => {
        const res = await apiPost("/api/discover", { url: demo ? (url || "demo://task-manager") : url, demo: !!demo });
        state.projectId = res.project_id;
        state.discovery = res.discovery;
      });
      await runPhase("analyze", async () => {
        const res = await apiPost("/api/analyze", { project_id: state.projectId });
        state.api = res.api;
      });
      await runPhase("design", async () => {
        const res = await apiPost("/api/design-tools", { project_id: state.projectId, demo: !!demo });
        state.design = res.design;
      });

      renderDiscoverySection();
      renderToolsSection();
      showEl(document.getElementById("discovery-section"));
      showEl(document.getElementById("tools-section"));
      document.getElementById("tools-section").scrollIntoView({ behavior: "smooth", block: "start" });
      showToast("Tools designed — review and generate your server", "success");
    } catch (err) {
      const failedStage = STAGES.find((s) => document.querySelector(`#stage-list [data-stage="${s.id}"]`)?.dataset.state === "running");
      if (failedStage) setStage(failedStage.id, "failed");
      showStageFailure(err.message);
    } finally {
      setBuilderFormBusy(false);
    }
  }

  function showStageFailure(message) {
    document.getElementById("stage-failure-message").textContent = message || "Please try again.";
    document.getElementById("stage-failure").hidden = false;
    showToast(message || "Something went wrong", "error");
  }

  function setBuilderFormBusy(busy) {
    const btn = document.getElementById("builder-submit");
    const label = document.getElementById("builder-submit-label");
    const input = document.getElementById("builder-url");
    if (btn) btn.disabled = busy;
    if (input) input.disabled = busy;
    const demoBtn = document.getElementById("builder-try-demo");
    const exBtn = document.getElementById("builder-fill-example");
    if (demoBtn) demoBtn.disabled = busy;
    if (exBtn) exBtn.disabled = busy;
    if (label) label.textContent = busy ? "Building…" : "Build MCP";
  }

  // ---------- discovery report ----------

  function renderDiscoverySection() {
    const api = state.api;
    if (!api) return;
    document.getElementById("disc-name").textContent = api.name || "—";
    document.getElementById("disc-base-url").textContent = api.base_url || "—";
    document.getElementById("disc-description").textContent = api.description || "";

    const authList = api.authentication || [];
    document.getElementById("disc-auth").textContent = authList.length
      ? authList.map((a) => authLabel(a.type)).join(", ")
      : "None detected";
    const authDetails = document.getElementById("disc-auth-details");
    authDetails.innerHTML = "";
    authList.forEach((a) => {
      const chip = document.createElement("span");
      chip.className = "badge badge-neutral";
      chip.textContent = [authLabel(a.type), a.header_name ? `header: ${a.header_name}` : null, a.scheme_name || null]
        .filter(Boolean).join(" · ");
      authDetails.appendChild(chip);
    });

    state.endpoints = api.endpoints || [];
    document.getElementById("disc-endpoint-count").textContent = `(${state.endpoints.length})`;
    state.methodFilter = new Set(state.endpoints.map((e) => e.method));
    renderMethodFilters();
    renderEndpointList();

    const schemaNames = Object.keys(api.schemas || {});
    const schemasCard = document.getElementById("schemas-card");
    if (schemaNames.length) {
      schemasCard.hidden = false;
      document.getElementById("disc-schema-count").textContent = `(${schemaNames.length})`;
      const list = document.getElementById("schema-list");
      list.innerHTML = "";
      schemaNames.forEach((name) => {
        const chip = document.createElement("span");
        chip.className = "badge badge-neutral font-mono";
        chip.textContent = name;
        list.appendChild(chip);
      });
    } else {
      schemasCard.hidden = true;
    }
  }

  function renderMethodFilters() {
    const methods = Array.from(new Set(state.endpoints.map((e) => e.method))).sort();
    const wrap = document.getElementById("endpoint-method-filters");
    wrap.innerHTML = "";
    methods.forEach((m) => {
      const btn = document.createElement("button");
      btn.type = "button";
      const active = state.methodFilter.has(m);
      btn.className = `badge cursor-pointer ${methodBadgeClass(m)} ${active ? "" : "opacity-40"}`;
      btn.setAttribute("aria-pressed", String(active));
      btn.textContent = m;
      btn.addEventListener("click", () => {
        if (state.methodFilter.has(m)) state.methodFilter.delete(m); else state.methodFilter.add(m);
        if (state.methodFilter.size === 0) methods.forEach((x) => state.methodFilter.add(x));
        renderMethodFilters();
        renderEndpointList();
      });
      wrap.appendChild(btn);
    });
  }

  function renderEndpointList() {
    const search = (document.getElementById("endpoint-search").value || "").toLowerCase();
    const list = document.getElementById("endpoint-list");
    const empty = document.getElementById("endpoint-empty");
    const filtered = state.endpoints.filter((e) =>
      state.methodFilter.has(e.method) &&
      (!search || e.path.toLowerCase().includes(search) || (e.summary || "").toLowerCase().includes(search) || (e.operation_id || "").toLowerCase().includes(search))
    );
    list.innerHTML = filtered.map((e) => `
      <div class="flex items-start gap-3 rounded-lg border border-line px-3 py-2.5">
        <span class="badge ${methodBadgeClass(e.method)} mt-0.5 shrink-0">${esc(e.method)}</span>
        <div class="min-w-0 flex-1">
          <div class="flex flex-wrap items-center gap-2">
            <span class="truncate font-mono text-sm text-ink">${esc(e.path)}</span>
            ${e.destructive ? '<span class="badge badge-danger">⚠ destructive</span>' : ""}
            ${e.deprecated ? '<span class="badge badge-warning">deprecated</span>' : ""}
          </div>
          ${e.summary ? `<p class="mt-0.5 truncate text-sm text-ink-secondary">${esc(e.summary)}</p>` : ""}
        </div>
      </div>`).join("");
    empty.classList.toggle("hidden", filtered.length !== 0);
  }

  // ---------- tool selection ----------

  function renderToolsSection() {
    const tools = (state.design && state.design.tools) || [];
    state.selectedToolNames = new Set(tools.filter((t) => t.selected !== false).map((t) => t.name));
    document.getElementById("pref-server-name").value = state.design.server_name || "";
    document.getElementById("pref-description").value = state.design.description || "";
    document.getElementById("tools-subtitle").textContent =
      `AI designed ${tools.length} tool${tools.length === 1 ? "" : "s"} from ${state.endpoints.length} endpoint${state.endpoints.length === 1 ? "" : "s"}. Review and deselect any you don't want.`;
    renderToolList(tools);
    updateToolsSelectedCount();
    document.getElementById("generate-btn").textContent = state.isGenerated ? "Regenerate Server" : "Generate Server";
  }

  function renderToolList(tools) {
    const container = document.getElementById("tool-list");
    const search = (document.getElementById("tool-search").value || "").toLowerCase();
    const filtered = tools.filter((t) => !search || t.name.toLowerCase().includes(search) || t.path.toLowerCase().includes(search));
    if (!filtered.length) {
      container.innerHTML = '<p class="py-6 text-center text-sm text-ink-tertiary">No tools match your search.</p>';
      return;
    }
    container.innerHTML = "";
    filtered.forEach((t) => {
      const checked = state.selectedToolNames.has(t.name);
      const label = document.createElement("label");
      label.className = "flex items-start gap-3 rounded-lg border border-line bg-surface p-3 hover:border-line-strong";
      label.innerHTML = `
        <input type="checkbox" class="tool-checkbox mt-1 h-4 w-4 rounded border-line-strong text-accent focus:ring-accent" ${checked ? "checked" : ""} />
        <span class="min-w-0 flex-1">
          <span class="flex flex-wrap items-center gap-2">
            <span class="font-mono text-sm font-semibold text-ink">${esc(t.name)}</span>
            <span class="badge ${methodBadgeClass(t.method)}">${esc(t.method)}</span>
            <span class="truncate font-mono text-xs text-ink-tertiary">${esc(t.path)}</span>
            ${t.destructive ? '<span class="badge badge-danger">⚠ destructive</span>' : ""}
          </span>
          <span class="mt-1 block text-sm text-ink-secondary">${esc(t.description || "")}</span>
        </span>`;
      const checkbox = label.querySelector("input");
      checkbox.addEventListener("change", () => {
        if (checkbox.checked) state.selectedToolNames.add(t.name); else state.selectedToolNames.delete(t.name);
        updateToolsSelectedCount();
      });
      container.appendChild(label);
    });
  }

  function updateToolsSelectedCount() {
    const count = state.selectedToolNames.size;
    document.getElementById("tools-selected-count").textContent = `${count} selected`;
    const btn = document.getElementById("generate-btn");
    btn.disabled = count === 0;
    btn.setAttribute("aria-disabled", String(count === 0));
    document.getElementById("generate-hint").textContent = count === 0 ? "Select at least one tool." : "";
  }

  function collectPreferences(selectedToolNames) {
    const includeDestructive = (state.design.tools || []).some((t) => t.destructive && selectedToolNames.includes(t.name));
    return {
      server_name: document.getElementById("pref-server-name").value.trim() || null,
      description: document.getElementById("pref-description").value.trim() || null,
      tool_naming_style: document.getElementById("pref-naming").value,
      include_read_only: document.getElementById("pref-read-only").checked,
      include_destructive: includeDestructive,
      group_by_resource: document.getElementById("pref-group").checked,
      generate_tests: document.getElementById("pref-tests").checked,
      generate_docs: document.getElementById("pref-docs").checked,
      selected_tool_names: selectedToolNames,
    };
  }

  async function handleGenerateClick() {
    if (!state.projectId) return;
    const selected = Array.from(state.selectedToolNames);
    if (!selected.length) { showToast("Select at least one tool first", "warning"); return; }
    const preferences = collectPreferences(selected);
    const btn = document.getElementById("generate-btn");
    const wasGenerated = state.isGenerated;
    btn.disabled = true;
    btn.textContent = wasGenerated ? "Regenerating…" : "Generating…";
    showEl(document.getElementById("stage-section"));
    setStage("generate", "running");
    setStage("validate", "waiting");
    try {
      const endpoint = wasGenerated ? "/api/regenerate" : "/api/generate";
      const res = await apiPost(endpoint, { project_id: state.projectId, preferences });
      state.generated = res.generated;
      state.validation = res.validation;
      state.lastSelectedToolNames = selected;
      state.isGenerated = true;
      setStage("generate", "done");
      setStage("validate", "done");

      const filesRes = await apiGet(`/api/project/${state.projectId}/files`);
      state.files = filesRes.files || [];

      renderResultSection();
      showEl(document.getElementById("result-section"));
      document.getElementById("result-section").scrollIntoView({ behavior: "smooth", block: "start" });
      showToast(wasGenerated ? "Server regenerated" : "Server generated and validated", res.validation.passed ? "success" : "warning");
    } catch (err) {
      setStage("generate", "failed");
      showToast(err.message || "Generation failed", "error");
    } finally {
      btn.disabled = false;
      btn.textContent = state.isGenerated ? "Regenerate Server" : "Generate Server";
    }
  }

  // ---------- result section (project explorer) ----------

  function renderResultSection() {
    const section = document.getElementById("result-section");
    const g = state.generated;
    const v = state.validation;
    const passed = !!(v && v.passed);
    const errCount = (v.errors || []).length;
    const warnCount = (v.warnings || []).length;
    section.innerHTML = `
      <div class="card p-5 sm:p-6 panel-enter">
        <div class="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p class="inline-flex items-center gap-1.5 text-sm font-semibold ${passed ? "text-success" : "text-danger"}">
              <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="${passed ? "M4.5 12.75l6 6 9-13.5" : "M6 6l12 12M18 6L6 18"}"/></svg>
              ${passed ? "MCP Server Ready" : "Validation failed"}
            </p>
            <h2 class="mt-1 text-2xl font-bold text-ink">${esc(g.server_name)}</h2>
            <p class="mt-1 text-sm text-ink-secondary">${g.tool_count} tool${g.tool_count === 1 ? "" : "s"} generated · ${errCount} error${errCount === 1 ? "" : "s"} · ${warnCount} warning${warnCount === 1 ? "" : "s"}</p>
            <p class="mt-1 text-xs text-ink-tertiary">Generated ${esc(new Date().toLocaleString())}</p>
          </div>
          <div class="flex flex-wrap gap-2">
            <a href="/api/project/${state.projectId}/download" class="btn bg-accent text-white hover:bg-accent-hover">Download Server</a>
            <button type="button" class="btn border border-line bg-surface text-ink hover:bg-surface-subtle" data-jump-tab="tools">View Tools</button>
            <button type="button" class="btn border border-line bg-surface text-ink hover:bg-surface-subtle" data-jump-tab="files">View Code</button>
            <button type="button" class="btn border border-line bg-surface text-ink hover:bg-surface-subtle" id="view-readme-btn">README</button>
            <a href="/project/${state.projectId}" class="btn border border-line bg-surface text-ink hover:bg-surface-subtle">Open project page</a>
          </div>
        </div>
      </div>

      <div class="card mt-6 overflow-hidden panel-enter">
        <div class="flex gap-1 overflow-x-auto border-b border-line px-4 pt-3" role="tablist" aria-label="Project sections">
          <button type="button" class="tab-btn" role="tab" id="tab-btn-files" aria-selected="true" aria-controls="tab-panel-files">Files</button>
          <button type="button" class="tab-btn" role="tab" id="tab-btn-tools" aria-selected="false" aria-controls="tab-panel-tools">Tools</button>
          <button type="button" class="tab-btn" role="tab" id="tab-btn-validation" aria-selected="false" aria-controls="tab-panel-validation">Validation</button>
        </div>
        <div id="tab-panel-files" role="tabpanel"></div>
        <div id="tab-panel-tools" role="tabpanel" hidden></div>
        <div id="tab-panel-validation" role="tabpanel" hidden></div>
      </div>

      <div class="card mt-6 p-5 sm:p-6 panel-enter" id="feedback-card">
        <h2 class="text-base font-semibold text-ink">How did this MCP server turn out?</h2>
        <div class="mt-3 flex items-center gap-1" id="feedback-stars" role="radiogroup" aria-label="Rating"></div>
        <label for="feedback-comment" class="sr-only">Feedback comment</label>
        <textarea id="feedback-comment" rows="2" placeholder="Optional comment…" class="mt-3 w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30"></textarea>
        <button type="button" id="feedback-submit" class="btn mt-3 border border-line-strong bg-surface text-ink hover:bg-surface-subtle">Submit feedback</button>
      </div>
    `;

    wireTabs();
    renderFilesTab();
    renderToolsTab();
    renderValidationTab();
    wireFeedback();

    document.getElementById("view-readme-btn")?.addEventListener("click", () => {
      switchTab("files");
      const readme = state.files.find((f) => /readme/i.test(f.path));
      if (readme) selectFile(readme.path);
    });
    section.querySelectorAll("[data-jump-tab]").forEach((btn) => {
      btn.addEventListener("click", () => switchTab(btn.getAttribute("data-jump-tab")));
    });
  }

  function switchTab(name) {
    ["files", "tools", "validation"].forEach((t) => {
      const panel = document.getElementById(`tab-panel-${t}`);
      if (panel) panel.hidden = t !== name;
      const btn = document.getElementById(`tab-btn-${t}`);
      if (btn) btn.setAttribute("aria-selected", String(t === name));
    });
  }

  function wireTabs() {
    ["files", "tools", "validation"].forEach((t) => {
      document.getElementById(`tab-btn-${t}`)?.addEventListener("click", () => switchTab(t));
    });
  }

  // ---------- files tab: tree + code viewer + metadata ----------

  function renderFilesTab() {
    const panel = document.getElementById("tab-panel-files");
    panel.innerHTML = `
      <div class="grid grid-cols-1 lg:grid-cols-[15rem_1fr_15rem]">
        <div class="border-b border-line p-3 lg:border-b-0 lg:border-r">
          <label for="file-search" class="sr-only">Search files</label>
          <input id="file-search" type="search" placeholder="Search files…" class="w-full rounded-lg border border-line bg-surface px-2.5 py-1.5 text-xs focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30" />
          <label for="mobile-file-select" class="sr-only">Choose a file</label>
          <select id="mobile-file-select" class="mt-2 w-full rounded-lg border border-line bg-surface px-2.5 py-1.5 text-xs lg:hidden"></select>
          <div id="file-tree" class="mt-2 hidden max-h-96 overflow-y-auto lg:block" role="tree" aria-label="Generated project files"></div>
        </div>
        <div class="min-w-0 border-b border-line lg:border-b-0 lg:border-r">
          <div class="flex items-center justify-between gap-2 border-b border-line bg-surface-subtle px-4 py-2">
            <span id="code-viewer-path" class="truncate font-mono text-xs text-ink-secondary">Select a file</span>
            <div class="flex shrink-0 gap-2">
              <button type="button" id="copy-file-btn" class="btn-icon text-ink-tertiary hover:bg-surface hover:text-ink" aria-label="Copy file contents" title="Copy file"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 012-2h10"/></svg></button>
              <button type="button" id="copy-all-btn" class="btn-icon text-ink-tertiary hover:bg-surface hover:text-ink" aria-label="Copy entire project" title="Copy all files"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 16H6a2 2 0 01-2-2V4a2 2 0 012-2h10a2 2 0 012 2v2M10 8h10a2 2 0 012 2v10a2 2 0 01-2 2H10a2 2 0 01-2-2V10a2 2 0 012-2z"/></svg></button>
            </div>
          </div>
          <div class="code-viewer max-h-96 overflow-auto lg:max-h-[32rem]"><pre><code id="code-viewer-code" class="language-plaintext"></code></pre></div>
        </div>
        <div class="p-4 text-sm" id="file-metadata-panel"></div>
      </div>
    `;

    renderFileMetadataPanel();
    buildAndRenderTree();

    document.getElementById("file-search").addEventListener("input", (e) => {
      state.fileSearch = e.target.value.toLowerCase();
      buildAndRenderTree();
    });
    document.getElementById("mobile-file-select").addEventListener("change", (e) => selectFile(e.target.value));
    document.getElementById("copy-file-btn").addEventListener("click", copyCurrentFile);
    document.getElementById("copy-all-btn").addEventListener("click", copyAllFiles);

    const first = state.files[0];
    if (first) selectFile(first.path);
  }

  function renderFileMetadataPanel() {
    const panel = document.getElementById("file-metadata-panel");
    if (!panel) return;
    const g = state.generated, v = state.validation, d = state.design;
    panel.innerHTML = `
      <h3 class="text-xs font-semibold uppercase tracking-wide text-ink-tertiary">Project</h3>
      <dl class="mt-2 space-y-2">
        <div><dt class="text-ink-tertiary">Server</dt><dd class="font-medium text-ink">${esc(g.server_name)}</dd></div>
        <div><dt class="text-ink-tertiary">Tools</dt><dd class="text-ink">${esc(g.tool_count)}</dd></div>
        <div><dt class="text-ink-tertiary">Auth</dt><dd class="text-ink">${esc(authLabel(d.auth_type))}</dd></div>
        <div><dt class="text-ink-tertiary">Base URL</dt><dd class="truncate font-mono text-xs text-ink">${esc(d.base_url || "")}</dd></div>
        <div><dt class="text-ink-tertiary">Validation</dt><dd><span class="badge ${v.passed ? "badge-success" : "badge-danger"}">${v.passed ? "Passed" : "Failed"}</span></dd></div>
      </dl>
      <a href="/api/project/${state.projectId}/download" class="btn mt-4 w-full justify-center bg-accent text-white hover:bg-accent-hover">Download .zip</a>
    `;
  }

  function buildFileTree(files) {
    const root = { name: "", path: "", type: "dir", children: new Map() };
    files.forEach((f) => {
      const parts = f.path.split("/");
      let node = root;
      parts.forEach((part, i) => {
        const isFile = i === parts.length - 1;
        if (!node.children.has(part)) {
          node.children.set(part, {
            name: part,
            path: node.path ? `${node.path}/${part}` : part,
            type: isFile ? "file" : "dir",
            children: new Map(),
          });
        }
        node = node.children.get(part);
      });
    });
    return root;
  }

  function sortedChildren(node) {
    return Array.from(node.children.values()).sort((a, b) => {
      if (a.type !== b.type) return a.type === "dir" ? -1 : 1;
      return a.name.localeCompare(b.name);
    });
  }

  function renderTreeNode(node, container) {
    sortedChildren(node).forEach((child) => {
      if (child.type === "dir") {
        const wrap = document.createElement("div");
        wrap.className = "tree-node";
        wrap.dataset.open = "true";
        const row = document.createElement("div");
        row.className = "tree-row";
        row.setAttribute("role", "treeitem");
        row.tabIndex = 0;
        row.innerHTML = `<svg class="tree-chevron h-3.5 w-3.5 shrink-0 text-ink-tertiary" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M9 6l6 6-6 6"/></svg><svg class="h-3.5 w-3.5 shrink-0 text-ink-tertiary" viewBox="0 0 24 24" fill="currentColor"><path d="M3 5.5A1.5 1.5 0 014.5 4h4.379a1.5 1.5 0 011.06.44l1.122 1.12A1.5 1.5 0 0012.12 6H19.5A1.5 1.5 0 0121 7.5v11A1.5 1.5 0 0119.5 20h-15A1.5 1.5 0 013 18.5v-13z"/></svg><span class="truncate">${esc(child.name)}</span>`;
        row.addEventListener("click", () => { wrap.dataset.open = wrap.dataset.open === "true" ? "false" : "true"; });
        row.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); row.click(); } });
        wrap.appendChild(row);
        const childrenEl = document.createElement("div");
        childrenEl.className = "tree-children";
        renderTreeNode(child, childrenEl);
        wrap.appendChild(childrenEl);
        container.appendChild(wrap);
      } else {
        const row = document.createElement("div");
        row.className = "tree-row";
        row.setAttribute("role", "treeitem");
        row.tabIndex = 0;
        row.setAttribute("aria-selected", String(state.currentFile === child.path));
        row.innerHTML = `<span class="w-3.5 shrink-0"></span><svg class="h-3.5 w-3.5 shrink-0 text-ink-tertiary" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><path d="M14 2v6h6"/></svg><span class="truncate">${esc(child.name)}</span>`;
        row.addEventListener("click", () => selectFile(child.path));
        row.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); selectFile(child.path); } });
        container.appendChild(row);
        state.fileTreeRows.set(child.path, row);
      }
    });
  }

  function buildAndRenderTree() {
    const search = state.fileSearch || "";
    const files = state.files.filter((f) => !search || f.path.toLowerCase().includes(search));
    const tree = buildFileTree(files);
    const container = document.getElementById("file-tree");
    container.innerHTML = "";
    state.fileTreeRows = new Map();
    renderTreeNode(tree, container);

    const select = document.getElementById("mobile-file-select");
    select.innerHTML = "";
    state.files.forEach((f) => {
      const opt = document.createElement("option");
      opt.value = f.path;
      opt.textContent = f.path;
      select.appendChild(opt);
    });
    if (state.currentFile) select.value = state.currentFile;
  }

  function selectFile(path) {
    const file = state.files.find((f) => f.path === path);
    if (!file) return;
    state.currentFile = path;
    document.getElementById("code-viewer-path").textContent = path;
    const codeEl = document.getElementById("code-viewer-code");
    codeEl.className = `language-${file.language || "plaintext"}`;
    codeEl.textContent = file.content || "";
    if (window.hljs) {
      codeEl.removeAttribute("data-highlighted");
      hljs.highlightElement(codeEl);
    }
    if (state.fileTreeRows) {
      state.fileTreeRows.forEach((row, p) => row.setAttribute("aria-selected", String(p === path)));
    }
    const select = document.getElementById("mobile-file-select");
    if (select) select.value = path;
  }

  async function copyText(text, successMessage) {
    try {
      await navigator.clipboard.writeText(text);
      showToast(successMessage, "success");
    } catch {
      showToast("Copy failed — clipboard permission denied", "error");
    }
  }

  function copyCurrentFile() {
    const file = state.files.find((f) => f.path === state.currentFile);
    if (!file) { showToast("Select a file first", "warning"); return; }
    copyText(file.content, `Copied ${file.path}`);
  }

  function copyAllFiles() {
    const combined = state.files.map((f) => `# ${f.path}\n${"-".repeat(Math.min(f.path.length + 2, 60))}\n${f.content}`).join("\n\n");
    copyText(combined, `Copied all ${state.files.length} files`);
  }

  // ---------- tools tab ----------

  function toolCardHtml(t) {
    const params = t.parameters || [];
    const rows = params.length
      ? params.map((p) => `<tr class="border-t border-line"><td class="py-1.5 pr-3 font-mono text-xs text-ink">${esc(p.name)}</td><td class="py-1.5 pr-3 text-xs text-ink-tertiary">${esc(p.type)}</td><td class="py-1.5 text-xs">${p.required ? '<span class="badge badge-warning">required</span>' : '<span class="text-ink-tertiary">optional</span>'}</td></tr>`).join("")
      : `<tr><td colspan="3" class="py-2 text-xs text-ink-tertiary">No parameters</td></tr>`;
    return `
      <div class="card p-4">
        <div class="flex flex-wrap items-center gap-2">
          <span class="font-mono text-sm font-semibold text-ink">${esc(t.name)}</span>
          <span class="badge ${methodBadgeClass(t.method)}">${esc(t.method)}</span>
          <span class="font-mono text-xs text-ink-tertiary">${esc(t.path)}</span>
          ${t.destructive ? '<span class="badge badge-danger">⚠ destructive</span>' : ""}
          <span class="badge badge-neutral">${esc(t.group || "general")}</span>
        </div>
        <p class="mt-2 text-sm text-ink-secondary">${esc(t.description)}</p>
        <table class="mt-3 w-full text-left">
          <thead><tr class="text-xs text-ink-tertiary"><th class="pb-1 font-medium">Input</th><th class="pb-1 font-medium">Type</th><th class="pb-1 font-medium"></th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
        <p class="mt-2 font-mono text-xs text-ink-tertiary">Source: ${esc(t.source_operation_id || "")}</p>
      </div>`;
  }

  function renderToolsTab() {
    const panel = document.getElementById("tab-panel-tools");
    const selectedNames = new Set(state.lastSelectedToolNames || []);
    const included = (state.design.tools || []).filter((t) => selectedNames.has(t.name));
    panel.innerHTML = `<div class="max-h-[34rem] space-y-3 overflow-y-auto p-4">${included.map(toolCardHtml).join("") || '<p class="text-sm text-ink-tertiary">No tools included.</p>'}</div>`;
  }

  // ---------- validation tab ----------

  function renderValidationTab() {
    const panel = document.getElementById("tab-panel-validation");
    const v = state.validation;
    const checks = (v.checks || []).map((c) => `
      <li class="flex items-start gap-3 rounded-lg border border-line px-3 py-2.5">
        <span class="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-xs font-bold ${c.passed ? "bg-success/15 text-success" : (c.severity === "warning" ? "bg-warning/15 text-warning" : "bg-danger/15 text-danger")}">${c.passed ? "✓" : (c.severity === "warning" ? "!" : "✕")}</span>
        <span class="min-w-0 flex-1">
          <span class="block text-sm font-medium text-ink">${esc(c.name)}</span>
          ${c.message ? `<span class="mt-0.5 block text-sm text-ink-secondary">${esc(c.message)}</span>` : ""}
        </span>
      </li>`).join("");
    panel.innerHTML = `
      <div class="p-4">
        <div class="mb-4 flex flex-wrap items-center gap-2 rounded-lg border p-3 ${v.passed ? "border-success-border bg-success-soft" : "border-danger-border bg-danger-soft"}">
          <span class="font-semibold ${v.passed ? "text-success" : "text-danger"}">${v.passed ? "All checks passed" : "Validation failed"}</span>
          <button type="button" id="revalidate-btn" class="btn ml-auto border border-line bg-surface px-3 py-1.5 text-xs text-ink hover:bg-surface-subtle">Re-run validation</button>
        </div>
        <ul class="space-y-2">${checks || '<li class="text-sm text-ink-tertiary">No checks recorded.</li>'}</ul>
      </div>`;
    document.getElementById("revalidate-btn")?.addEventListener("click", handleRevalidate);
  }

  async function handleRevalidate() {
    const btn = document.getElementById("revalidate-btn");
    btn.disabled = true;
    btn.textContent = "Validating…";
    try {
      const res = await apiPost("/api/validate", { project_id: state.projectId });
      state.validation = res.validation;
      renderValidationTab();
      renderFileMetadataPanel();
      showToast("Validation complete", res.validation.passed ? "success" : "warning");
    } catch (err) {
      showToast(err.message || "Validation failed", "error");
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  // ---------- feedback ----------

  function wireFeedback() {
    const starsWrap = document.getElementById("feedback-stars");
    state.rating = 0;
    starsWrap.innerHTML = "";
    for (let i = 1; i <= 5; i++) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "btn-icon text-line-strong hover:text-warning";
      btn.setAttribute("role", "radio");
      btn.setAttribute("aria-checked", "false");
      btn.setAttribute("aria-label", `${i} star${i > 1 ? "s" : ""}`);
      btn.innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01z"/></svg>';
      btn.addEventListener("click", () => {
        state.rating = i;
        Array.from(starsWrap.children).forEach((el, idx) => {
          el.classList.toggle("text-warning", idx < i);
          el.classList.toggle("text-line-strong", idx >= i);
          el.setAttribute("aria-checked", String(idx < i));
        });
      });
      starsWrap.appendChild(btn);
    }
    document.getElementById("feedback-submit").addEventListener("click", submitFeedback);
  }

  async function submitFeedback() {
    if (!state.rating) { showToast("Pick a rating first", "warning"); return; }
    const comment = document.getElementById("feedback-comment").value.trim();
    const btn = document.getElementById("feedback-submit");
    btn.disabled = true;
    try {
      await apiPost(`/api/project/${state.projectId}/feedback`, { rating: state.rating, comment });
      showToast("Thanks for the feedback!", "success");
      btn.textContent = "Feedback sent";
    } catch (err) {
      showToast(err.message || "Failed to send feedback", "error");
      btn.disabled = false;
    }
  }

  // ---------- wiring ----------

  document.addEventListener("DOMContentLoaded", () => {
    renderStageList();
    renderBuilderRecentUrls();

    document.getElementById("builder-url-form").addEventListener("submit", (e) => {
      e.preventDefault();
      const input = document.getElementById("builder-url");
      const url = input.value.trim();
      const errorEl = document.getElementById("builder-url-error");
      if (!isPlausibleUrl(url)) {
        errorEl.textContent = "Enter a full URL, including https://";
        errorEl.classList.remove("hidden");
        input.setAttribute("aria-invalid", "true");
        input.focus();
        return;
      }
      errorEl.classList.add("hidden");
      input.removeAttribute("aria-invalid");
      pushRecentUrl(url);
      renderBuilderRecentUrls();
      window.history.replaceState(null, "", "/builder?url=" + encodeURIComponent(url));
      startPipeline(url, false);
    });

    document.getElementById("builder-try-demo").addEventListener("click", () => {
      window.history.replaceState(null, "", "/builder?demo=1");
      startPipeline("", true);
    });

    document.getElementById("builder-fill-example").addEventListener("click", () => {
      const input = document.getElementById("builder-url");
      input.value = EXAMPLE_URL;
      input.focus();
    });

    document.getElementById("stage-retry").addEventListener("click", () => {
      document.getElementById("stage-failure").hidden = true;
      const params = new URLSearchParams(window.location.search);
      const url = document.getElementById("builder-url").value.trim();
      const demo = params.get("demo") === "1" && !url;
      startPipeline(demo ? "" : url, demo);
    });

    document.getElementById("endpoint-search").addEventListener("input", renderEndpointList);
    document.getElementById("tool-search").addEventListener("input", () => renderToolList(state.design.tools));
    document.getElementById("tools-select-all").addEventListener("click", () => {
      state.selectedToolNames = new Set(state.design.tools.map((t) => t.name));
      renderToolList(state.design.tools);
      updateToolsSelectedCount();
    });
    document.getElementById("tools-select-none").addEventListener("click", () => {
      state.selectedToolNames = new Set();
      renderToolList(state.design.tools);
      updateToolsSelectedCount();
    });
    document.getElementById("tools-select-safe").addEventListener("click", () => {
      state.selectedToolNames = new Set(state.design.tools.filter((t) => !t.destructive).map((t) => t.name));
      renderToolList(state.design.tools);
      updateToolsSelectedCount();
    });
    document.getElementById("generate-btn").addEventListener("click", handleGenerateClick);

    document.getElementById("new-build-link").addEventListener("click", (e) => {
      if (state.projectId) {
        e.preventDefault();
        showConfirm("Start a new build?", "The current project stays saved in History, but this page will reset.", () => {
          window.location.href = "/builder";
        });
      }
    });

    const params = new URLSearchParams(window.location.search);
    if (params.get("demo") === "1") {
      startPipeline("", true);
    } else if (params.get("url")) {
      document.getElementById("builder-url").value = params.get("url");
    }
  });
})();
