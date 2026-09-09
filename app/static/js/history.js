// History page: fetch GET /api/history, client-side search/filter, delete with confirm.
(() => {
  "use strict";

  const state = {
    projects: [],
    search: "",
    statusFilter: "all",
  };

  function esc(str) {
    return String(str ?? "").replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
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

  function relativeTime(iso) {
    if (!iso) return "";
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return "";
    const diffMs = Date.now() - date.getTime();
    const minutes = Math.round(diffMs / 60000);
    if (minutes < 1) return "just now";
    if (minutes < 60) return `${minutes} minute${minutes === 1 ? "" : "s"} ago`;
    const hours = Math.round(minutes / 60);
    if (hours < 24) return `${hours} hour${hours === 1 ? "" : "s"} ago`;
    const days = Math.round(hours / 24);
    if (days < 30) return `${days} day${days === 1 ? "" : "s"} ago`;
    return date.toLocaleDateString();
  }

  function statusBadgeClass(status) {
    if (status === "ready") return "badge-success";
    if (status === "failed") return "badge-danger";
    return "badge-warning";
  }

  async function loadHistory() {
    document.getElementById("history-loading").classList.remove("hidden");
    document.getElementById("history-error").classList.add("hidden");
    document.getElementById("history-empty").classList.add("hidden");
    document.getElementById("history-list").innerHTML = "";
    try {
      const res = await fetch("/api/history");
      const data = await res.json();
      if (!res.ok) throw new Error(data?.detail || `Request failed (${res.status})`);
      state.projects = data.projects || [];
      document.getElementById("history-count").textContent = `${data.total ?? state.projects.length} project${(data.total ?? state.projects.length) === 1 ? "" : "s"}`;
      renderStatusFilters();
      render();
    } catch (err) {
      document.getElementById("history-error-message").textContent = err.message || "Please try again.";
      document.getElementById("history-error").classList.remove("hidden");
    } finally {
      document.getElementById("history-loading").classList.add("hidden");
    }
  }

  function renderStatusFilters() {
    const statuses = ["all", ...new Set(state.projects.map((p) => p.status))];
    const wrap = document.getElementById("status-filters");
    wrap.innerHTML = "";
    statuses.forEach((s) => {
      const btn = document.createElement("button");
      btn.type = "button";
      const active = state.statusFilter === s;
      btn.className = `badge cursor-pointer ${active ? "badge-neutral font-semibold" : "badge-neutral opacity-50"}`;
      btn.textContent = s === "all" ? "All" : s;
      btn.setAttribute("aria-pressed", String(active));
      btn.addEventListener("click", () => { state.statusFilter = s; renderStatusFilters(); render(); });
      wrap.appendChild(btn);
    });
  }

  function render() {
    const list = document.getElementById("history-list");
    const search = state.search.toLowerCase();
    const filtered = state.projects.filter((p) =>
      (state.statusFilter === "all" || p.status === state.statusFilter) &&
      (!search || (p.server_name || "").toLowerCase().includes(search))
    );

    document.getElementById("history-empty").classList.toggle("hidden", state.projects.length !== 0);
    document.getElementById("history-no-results").classList.toggle("hidden", !(state.projects.length && filtered.length === 0));

    list.innerHTML = filtered.map((p) => `
      <li class="card flex flex-wrap items-center justify-between gap-4 p-4 sm:p-5">
        <a href="/project/${encodeURIComponent(p.id)}" class="min-w-0 flex-1">
          <div class="flex flex-wrap items-center gap-2">
            <span class="truncate text-base font-semibold text-ink">${esc(p.server_name || "Untitled server")}</span>
            <span class="badge ${statusBadgeClass(p.status)}">${esc(p.status)}</span>
          </div>
          <p class="mt-1 text-sm text-ink-secondary">${esc(p.tool_count ?? 0)} tool${(p.tool_count ?? 0) === 1 ? "" : "s"} · ${esc(relativeTime(p.created_at))}</p>
        </a>
        <div class="flex shrink-0 items-center gap-2">
          <a href="/project/${encodeURIComponent(p.id)}" class="btn border border-line bg-surface px-3 py-1.5 text-xs text-ink hover:bg-surface-subtle">Open</a>
          <button type="button" class="btn-icon text-ink-tertiary hover:bg-danger-soft hover:text-danger" data-delete-id="${esc(p.id)}" aria-label="Delete ${esc(p.server_name || "project")}" title="Delete project">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 7h12M9 7V5a1 1 0 011-1h4a1 1 0 011 1v2m2 0v13a2 2 0 01-2 2H8a2 2 0 01-2-2V7h12z"/></svg>
          </button>
        </div>
      </li>`).join("");

    list.querySelectorAll("[data-delete-id]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const id = btn.getAttribute("data-delete-id");
        const project = state.projects.find((p) => p.id === id);
        showConfirm(
          "Delete this project?",
          `"${project?.server_name || "This project"}" and its generated files will be permanently removed.`,
          () => deleteProject(id)
        );
      });
    });
  }

  async function deleteProject(id) {
    try {
      const res = await fetch(`/api/project/${encodeURIComponent(id)}`, { method: "DELETE" });
      const data = await res.json().catch(() => null);
      if (!res.ok) throw new Error(data?.detail || `Request failed (${res.status})`);
      state.projects = state.projects.filter((p) => p.id !== id);
      document.getElementById("history-count").textContent = `${state.projects.length} project${state.projects.length === 1 ? "" : "s"}`;
      renderStatusFilters();
      render();
      showToast("Project deleted", "success");
    } catch (err) {
      showToast(err.message || "Failed to delete project", "error");
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    loadHistory();
    document.getElementById("history-search").addEventListener("input", (e) => {
      state.search = e.target.value;
      render();
    });
    document.getElementById("history-retry").addEventListener("click", loadHistory);

    const dialog = document.getElementById("confirm-dialog");
    dialog?.addEventListener("click", (e) => {
      if (e.target === dialog) document.getElementById("confirm-cancel")?.click();
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && dialog && !dialog.hidden) document.getElementById("confirm-cancel")?.click();
    });
  });
})();
