// Home page: hero URL form, recent-URLs (localStorage), example URL fill-in.
(() => {
  "use strict";

  const RECENT_KEY = "mcp-builder:recent-urls";
  const EXAMPLE_URL = "https://petstore3.swagger.io/api/v3/openapi.json";
  const MAX_RECENT = 5;

  function readRecent() {
    try {
      const raw = localStorage.getItem(RECENT_KEY);
      const list = raw ? JSON.parse(raw) : [];
      return Array.isArray(list) ? list : [];
    } catch {
      return [];
    }
  }

  function writeRecent(list) {
    try {
      localStorage.setItem(RECENT_KEY, JSON.stringify(list.slice(0, MAX_RECENT)));
    } catch {
      /* localStorage unavailable — recent URLs simply won't persist */
    }
  }

  function pushRecent(url) {
    const list = readRecent().filter((u) => u !== url);
    list.unshift(url);
    writeRecent(list);
  }

  function isPlausibleUrl(value) {
    if (!value) return false;
    try {
      const parsed = new URL(value);
      return parsed.protocol === "http:" || parsed.protocol === "https:";
    } catch {
      return false;
    }
  }

  function renderRecent() {
    const wrap = document.getElementById("recent-urls");
    const list = document.getElementById("recent-urls-list");
    if (!wrap || !list) return;
    const urls = readRecent();
    if (urls.length === 0) {
      wrap.classList.add("hidden");
      return;
    }
    wrap.classList.remove("hidden");
    list.innerHTML = "";
    urls.forEach((url) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className =
        "max-w-[16rem] truncate rounded-full border border-line bg-surface px-3 py-1.5 font-mono text-xs text-ink-secondary hover:border-line-strong hover:text-ink";
      btn.textContent = url;
      btn.title = url;
      btn.addEventListener("click", () => {
        const input = document.getElementById("hero-url");
        if (input) {
          input.value = url;
          input.focus();
        }
      });
      list.appendChild(btn);
    });
  }

  function goToBuilder(url) {
    pushRecent(url);
    window.location.href = "/builder?url=" + encodeURIComponent(url);
  }

  function initHeroForm() {
    const form = document.getElementById("hero-url-form");
    const input = document.getElementById("hero-url");
    const error = document.getElementById("hero-url-error");
    const exampleBtn = document.getElementById("hero-fill-example");
    if (!form || !input) return;

    exampleBtn?.addEventListener("click", () => {
      input.value = EXAMPLE_URL;
      input.focus();
      error?.classList.add("hidden");
    });

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const url = input.value.trim();
      if (!isPlausibleUrl(url)) {
        if (error) {
          error.textContent = "Enter a full URL, including https://";
          error.classList.remove("hidden");
        }
        input.setAttribute("aria-invalid", "true");
        input.focus();
        return;
      }
      error?.classList.add("hidden");
      input.removeAttribute("aria-invalid");
      goToBuilder(url);
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    initHeroForm();
    renderRecent();
  });
})();
