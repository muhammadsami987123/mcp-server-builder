// Project detail page: loads a single project from the real API and renders
// file tree + code viewer, tool inspector, discovery report, and validation report.
(() => {
  "use strict";

  const body = document.body;
  if (body.dataset.notFound === "true") return;

  const projectId = body.dataset.projectId;
  const state = {
    project: null,
    files: [],
    tools: [],
    currentFile: null,
    fileSearch: "",
    fileTreeRows: null,
    endpoints: [],
    methodFilter: null,
    rating: 0,
  };

  // ---------- helpers (shared shape with builder.js, page loads independently) ----------

  function esc(str) {
    return String(str ?? "").replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
  }

  function methodBadgeClass(method) {
    const map = { GET: "badge-method-get", POST: "badge-method-post", PUT: "badge-method-put", PATCH: "badge-method-patch", DELETE: "badge-method-delete" };
    return map[method] || "badge-neutral";
  }

  function authLabel(type) {
    const map = { api_key: "API Key", bearer: "Bearer Token", basic: "Basic Auth", oauth2: "OAuth 2.0", none: "None", unknown: "Unknown" };
    return map[type] || type || "Unknown";
  }

  function statusBadgeClass(status) {
    if (status === "ready") return "badge-success";
    if (status === "failed") return "badge-danger";
    return "badge-warning";
  }

  async function apiGet(path) {
    const res = await fetch(path);
    let data = null;
    try { data = await res.json(); } catch { /* no body */ }
    if (!res.ok) throw new Error((data && data.detail) || `Request failed (${res.status})`);
    return data;
  }

  async function apiPost(path, body) {
    const res = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) });
    let data = null;
    try { data = await res.json(); } catch { /* no body */ }
    if (!res.ok) throw new Error((data && data.detail) || `Request failed (${res.status})`);
    return data;
  }

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

  // ---------- load ----------

  async function loadProject() {
    document.getElementById("project-loading").classList.remove("hidden");
    document.getElementById("project-error").classList.add("hidden");
    document.getElementById("project-content").classList.add("hidden");
    try {
      const project = await apiGet(`/api/project/${encodeURIComponent(projectId)}`);
      state.project = project;

      const [filesRes, toolsRes] = await Promise.all([
        project.generated ? apiGet(`/api/project/${encodeURIComponent(projectId)}/files`) : Promise.resolve({ files: [] }),
        project.design ? apiGet(`/api/project/${encodeURIComponent(projectId)}/tools`) : Promise.resolve({ tools: [] }),
      ]);
      state.files = filesRes.files || [];
      state.tools = toolsRes.tools || [];

      renderHeader();
      wireTabs();
      renderFilesTab();
      renderToolsTab();
      renderDiscoveryTab();
      renderValidationTab();
      wireFeedback();

      document.getElementById("project-content").classList.remove("hidden");
    } catch (err) {
      document.getElementById("project-error-message").textContent = err.message || "Please try again.";
      document.getElementById("project-error").classList.remove("hidden");
    } finally {
      document.getElementById("project-loading").classList.add("hidden");
    }
  }

  function includedToolNames() {
    const fromPrefs = state.project?.preferences?.selected_tool_names;
    if (Array.isArray(fromPrefs)) return new Set(fromPrefs);
    return new Set(state.tools.filter((t) => t.selected !== false).map((t) => t.name));
  }

  // ---------- header ----------

  function renderHeader() {
    const p = state.project;
    const design = p.design || {};
    const generated = p.generated || {};
    const validation = p.validation;
    const serverName = generated.server_name || design.server_name || "Untitled server";

    document.getElementById("proj-name").textContent = serverName;
    const statusBadge = document.getElementById("proj-status-badge");
    statusBadge.textContent = p.status;
    statusBadge.className = `badge ${statusBadgeClass(p.status)}`;
    document.getElementById("proj-source-url").textContent = p.source_url || "";

    const toolCount = generated.tool_count ?? design.tools?.length ?? 0;
    const errCount = validation?.errors?.length ?? 0;
    const warnCount = validation?.warnings?.length ?? 0;
    document.getElementById("proj-summary").textContent = p.error_message
      ? p.error_message
      : `${toolCount} tool${toolCount === 1 ? "" : "s"} · ${errCount} error${errCount === 1 ? "" : "s"} · ${warnCount} warning${warnCount === 1 ? "" : "s"}`;

    const created = p.created_at ? new Date(p.created_at).toLocaleString() : "";
    const updated = p.updated_at ? new Date(p.updated_at).toLocaleString() : "";
    document.getElementById("proj-timestamps").textContent = `Created ${created}${updated && updated !== created ? ` · Updated ${updated}` : ""}`;

    const downloadBtn = document.getElementById("proj-download-btn");
    if (p.generated) {
      downloadBtn.href = `/api/project/${encodeURIComponent(projectId)}/download`;
    } else {
      downloadBtn.removeAttribute("href");
      downloadBtn.classList.add("opacity-50", "pointer-events-none");
      downloadBtn.setAttribute("aria-disabled", "true");
    }

    document.querySelectorAll("[data-jump-tab]").forEach((btn) => {
      btn.addEventListener("click", () => switchTab(btn.getAttribute("data-jump-tab")));
    });

    document.getElementById("proj-delete-btn").addEventListener("click", () => {
      showConfirm("Delete this project?", `"${serverName}" and its generated files will be permanently removed.`, deleteProject);
    });
  }

  async function deleteProject() {
    try {
      await apiGet(`/api/project/${encodeURIComponent(projectId)}`); // ensure still exists
    } catch { /* proceed to delete regardless */ }
    try {
      const res = await fetch(`/api/project/${encodeURIComponent(projectId)}`, { method: "DELETE" });
      const data = await res.json().catch(() => null);
      if (!res.ok) throw new Error((data && data.detail) || `Request failed (${res.status})`);
      showToast("Project deleted", "success");
      window.location.href = "/history";
    } catch (err) {
      showToast(err.message || "Failed to delete project", "error");
    }
  }

  // ---------- tabs ----------

  function switchTab(name) {
    ["files", "tools", "discovery", "validation"].forEach((t) => {
      const panel = document.getElementById(`tab-panel-${t}`);
      if (panel) panel.hidden = t !== name;
      const btn = document.getElementById(`tab-btn-${t}`);
      if (btn) btn.setAttribute("aria-selected", String(t === name));
    });
  }

  function wireTabs() {
    ["files", "tools", "discovery", "validation"].forEach((t) => {
      document.getElementById(`tab-btn-${t}`)?.addEventListener("click", () => switchTab(t));
    });
  }

  // ---------- files tab ----------

  function renderFilesTab() {
    const panel = document.getElementById("tab-panel-files");
    if (!state.files.length) {
      panel.innerHTML = '<p class="p-6 text-sm text-ink-tertiary">No generated files yet.</p>';
      return;
    }
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

    const readme = state.files.find((f) => /readme/i.test(f.path));
    selectFile((readme || state.files[0]).path);
  }

  function renderFileMetadataPanel() {
    const panel = document.getElementById("file-metadata-panel");
    if (!panel) return;
    const p = state.project;
    const g = p.generated || {};
    const v = p.validation;
    const d = p.design || {};
    panel.innerHTML = `
      <h3 class="text-xs font-semibold uppercase tracking-wide text-ink-tertiary">Project</h3>
      <dl class="mt-2 space-y-2">
        <div><dt class="text-ink-tertiary">Server</dt><dd class="font-medium text-ink">${esc(g.server_name || d.server_name || "")}</dd></div>
        <div><dt class="text-ink-tertiary">Tools</dt><dd class="text-ink">${esc(g.tool_count ?? "—")}</dd></div>
        <div><dt class="text-ink-tertiary">Auth</dt><dd class="text-ink">${esc(authLabel(d.auth_type))}</dd></div>
        <div><dt class="text-ink-tertiary">Base URL</dt><dd class="truncate font-mono text-xs text-ink">${esc(d.base_url || "")}</dd></div>
        <div><dt class="text-ink-tertiary">Validation</dt><dd>${v ? `<span class="badge ${v.passed ? "badge-success" : "badge-danger"}">${v.passed ? "Passed" : "Failed"}</span>` : '<span class="text-ink-tertiary">Not run</span>'}</dd></div>
      </dl>
      <a href="/api/project/${encodeURIComponent(projectId)}/download" class="btn mt-4 w-full justify-center bg-accent text-white hover:bg-accent-hover">Download .zip</a>
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
          node.children.set(part, { name: part, path: node.path ? `${node.path}/${part}` : part, type: isFile ? "file" : "dir", children: new Map() });
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
    if (!state.tools.length) {
      panel.innerHTML = '<p class="p-6 text-sm text-ink-tertiary">No tools designed yet.</p>';
      return;
    }
    const included = includedToolNames();
    const shown = state.project.generated ? state.tools.filter((t) => included.has(t.name)) : state.tools;
    panel.innerHTML = `
      <div class="p-4">
        <label for="tool-search" class="sr-only">Search tools</label>
        <input id="tool-search" type="search" placeholder="Search tools…" class="mb-3 w-full max-w-xs rounded-lg border border-line bg-surface px-2.5 py-1.5 text-xs focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30" />
        <div id="tool-cards" class="max-h-[32rem] space-y-3 overflow-y-auto">${shown.map(toolCardHtml).join("") || '<p class="text-sm text-ink-tertiary">No tools included in this build.</p>'}</div>
      </div>`;
    document.getElementById("tool-search").addEventListener("input", (e) => {
      const q = e.target.value.toLowerCase();
      const filtered = shown.filter((t) => t.name.toLowerCase().includes(q) || t.path.toLowerCase().includes(q));
      document.getElementById("tool-cards").innerHTML = filtered.map(toolCardHtml).join("") || '<p class="text-sm text-ink-tertiary">No tools match your search.</p>';
    });
  }

  // ---------- discovery tab ----------

  function renderDiscoveryTab() {
    const panel = document.getElementById("tab-panel-discovery");
    const api = state.project.api;
    if (!api) {
      panel.innerHTML = '<p class="p-6 text-sm text-ink-tertiary">No discovery data available.</p>';
      return;
    }
    state.endpoints = api.endpoints || [];
    state.methodFilter = new Set(state.endpoints.map((e) => e.method));
    const schemaNames = Object.keys(api.schemas || {});
    const authList = api.authentication || [];

    panel.innerHTML = `
      <div class="space-y-6 p-4">
        <div>
          <dl class="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div><dt class="text-xs font-semibold uppercase tracking-wide text-ink-tertiary">API name</dt><dd class="mt-1 truncate font-medium text-ink">${esc(api.name || "—")}</dd></div>
            <div><dt class="text-xs font-semibold uppercase tracking-wide text-ink-tertiary">Base URL</dt><dd class="mt-1 truncate font-mono text-sm text-ink">${esc(api.base_url || "—")}</dd></div>
            <div><dt class="text-xs font-semibold uppercase tracking-wide text-ink-tertiary">Authentication</dt><dd class="mt-1 text-ink">${authList.length ? esc(authList.map((a) => authLabel(a.type)).join(", ")) : "None detected"}</dd></div>
          </dl>
          ${api.description ? `<p class="mt-3 text-sm leading-relaxed text-ink-secondary">${esc(api.description)}</p>` : ""}
        </div>
        ${schemaNames.length ? `
        <div>
          <h3 class="text-xs font-semibold uppercase tracking-wide text-ink-tertiary">Schemas (${schemaNames.length})</h3>
          <div class="mt-2 flex flex-wrap gap-2">${schemaNames.map((n) => `<span class="badge badge-neutral font-mono">${esc(n)}</span>`).join("")}</div>
        </div>` : ""}
        <div>
          <div class="flex flex-wrap items-center justify-between gap-3">
            <h3 class="text-xs font-semibold uppercase tracking-wide text-ink-tertiary">Endpoints (${state.endpoints.length})</h3>
            <input id="disc-endpoint-search" type="search" placeholder="Search endpoints…" class="w-48 rounded-lg border border-line bg-surface px-2.5 py-1.5 text-xs focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30" />
          </div>
          <div id="disc-method-filters" class="mt-2 flex flex-wrap gap-2"></div>
          <div id="disc-endpoint-list" class="mt-3 max-h-96 space-y-2 overflow-y-auto pr-1"></div>
        </div>
      </div>`;

    renderDiscMethodFilters();
    renderDiscEndpointList();
    document.getElementById("disc-endpoint-search").addEventListener("input", renderDiscEndpointList);
  }

  function renderDiscMethodFilters() {
    const methods = Array.from(new Set(state.endpoints.map((e) => e.method))).sort();
    const wrap = document.getElementById("disc-method-filters");
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
        renderDiscMethodFilters();
        renderDiscEndpointList();
      });
      wrap.appendChild(btn);
    });
  }

  function renderDiscEndpointList() {
    const search = (document.getElementById("disc-endpoint-search")?.value || "").toLowerCase();
    const list = document.getElementById("disc-endpoint-list");
    const filtered = state.endpoints.filter((e) =>
      state.methodFilter.has(e.method) &&
      (!search || e.path.toLowerCase().includes(search) || (e.summary || "").toLowerCase().includes(search))
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
      </div>`).join("") || '<p class="text-sm text-ink-tertiary">No endpoints match your search.</p>';
  }

  // ---------- validation tab ----------

  function renderValidationTab() {
    const panel = document.getElementById("tab-panel-validation");
    const v = state.project.validation;
    if (!v) {
      panel.innerHTML = '<p class="p-6 text-sm text-ink-tertiary">This project hasn\'t been validated yet.</p>';
      return;
    }
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
      const res = await apiPost("/api/validate", { project_id: projectId });
      state.project.validation = res.validation;
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
      await apiPost(`/api/project/${encodeURIComponent(projectId)}/feedback`, { rating: state.rating, comment });
      showToast("Thanks for the feedback!", "success");
      btn.textContent = "Feedback sent";
    } catch (err) {
      showToast(err.message || "Failed to send feedback", "error");
      btn.disabled = false;
    }
  }

  // ---------- init ----------

  document.addEventListener("DOMContentLoaded", () => {
    loadProject();
    document.getElementById("project-retry")?.addEventListener("click", loadProject);

    const dialog = document.getElementById("confirm-dialog");
    dialog?.addEventListener("click", (e) => {
      if (e.target === dialog) document.getElementById("confirm-cancel")?.click();
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && dialog && !dialog.hidden) document.getElementById("confirm-cancel")?.click();
    });
  });
})();
