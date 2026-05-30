/**
 * market_search.js — live search dropdown + переход на страницу актива.
 *
 * initMarketSearch({ type, baseUrl, searchUrl, appGameSelectId?, appIdInputId?, appSelectId? })
 */
"use strict";

const MARKET_SEARCH_LIMIT = 10;

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function initMarketSearch(config) {
  const input = document.getElementById("marketSearchInput");
  const button = document.getElementById("marketSearchBtn");
  const dropdown = document.getElementById("marketSearchDropdown");
  if (!input || !dropdown || !config?.baseUrl || !config?.searchUrl) return;

  const baseUrl = config.baseUrl.endsWith("/")
    ? config.baseUrl
    : `${config.baseUrl}/`;

  let activeController = null;
  let requestSeq = 0;

  function steamAppIdFromFilters() {
    const gameSelect = config.appGameSelectId
      ? document.getElementById(config.appGameSelectId)
      : null;
    const customInput = config.appIdInputId
      ? document.getElementById(config.appIdInputId)
      : null;

    if (gameSelect) {
      if (gameSelect.value === "custom") {
        const val = customInput?.value.trim() || "";
        return /^\d+$/.test(val) ? val : "730";
      }
      return gameSelect.value || "730";
    }

    if (customInput) {
      const val = customInput.value.trim();
      if (/^\d+$/.test(val)) {
        return val;
      }
      return "730";
    }

    const select = config.appSelectId
      ? document.getElementById(config.appSelectId)
      : null;
    let appId = (select?.value || "730").trim();
    if (appId === "all") {
      appId = "730";
    }
    return appId;
  }

  function steamAppIdForResult(result) {
    if (result?.app_id != null && String(result.app_id).trim() !== "") {
      return String(result.app_id);
    }
    return steamAppIdFromFilters();
  }

  function syncCustomAppIdField() {
    const gameSelect = config.appGameSelectId
      ? document.getElementById(config.appGameSelectId)
      : null;
    const customInput = config.appIdInputId
      ? document.getElementById(config.appIdInputId)
      : null;
    if (!gameSelect || !customInput) return;

    const isCustom = gameSelect.value === "custom";
    customInput.hidden = !isCustom;
    if (isCustom) {
      customInput.focus();
    }
  }

  function detailPath(result) {
    if (!result?.name) return null;

    if (config.type === "stock") {
      return `${baseUrl}${encodeURIComponent(String(result.name).toUpperCase())}/`;
    }
    if (config.type === "crypto") {
      return `${baseUrl}${encodeURIComponent(String(result.name).toLowerCase())}/`;
    }
    if (config.type === "steam") {
      return `${baseUrl}${steamAppIdForResult(result)}/${encodeURIComponent(result.name)}/`;
    }
    return null;
  }

  function assetPath(query) {
    const q = query.trim();
    if (!q) return null;

    if (config.type === "stock") {
      return `${baseUrl}${encodeURIComponent(q.toUpperCase())}/`;
    }
    if (config.type === "crypto") {
      return `${baseUrl}${encodeURIComponent(q.toLowerCase())}/`;
    }
    if (config.type === "steam") {
      return `${baseUrl}${steamAppIdFromFilters()}/${encodeURIComponent(q)}/`;
    }
    return null;
  }

  function primaryLabel(result) {
    if (config.type === "crypto") {
      return result.symbol || result.name || "";
    }
    if (config.type === "stock") {
      return result.name || "";
    }
    return result.name || "";
  }

  function secondaryLabel(result) {
    if (config.type === "steam") {
      return result.game || "";
    }
    const primary = primaryLabel(result);
    const full = result.full_name || "";
    if (!full || full === primary) {
      return "";
    }
    return full;
  }

  function setDropdownOpen(open) {
    dropdown.hidden = !open;
    dropdown.classList.toggle("is-open", open);
  }

  function renderDropdownMessage(text) {
    dropdown.innerHTML = `<div class="market-search-dropdown__msg">${escapeHtml(text)}</div>`;
    setDropdownOpen(true);
  }

  function renderDropdownResults(results) {
    if (!results.length) {
      renderDropdownMessage("No results found");
      return;
    }

    dropdown.innerHTML = results
      .map((result) => {
        const href = detailPath(result);
        if (!href) return "";
        const primary = primaryLabel(result);
        const secondary = secondaryLabel(result);
        return `
<a href="${escapeHtml(href)}" class="market-search-hit">
  <span class="market-search-hit__primary">${escapeHtml(primary)}</span>
  ${
    secondary
      ? `<span class="market-search-hit__secondary">${escapeHtml(secondary)}</span>`
      : ""
  }
</a>`;
      })
      .join("");

    setDropdownOpen(true);
  }

  function closeDropdown() {
    setDropdownOpen(false);
    dropdown.innerHTML = "";
  }

  async function runSearch(query) {
    const seq = ++requestSeq;
    if (activeController) {
      activeController.abort();
    }
    activeController = new AbortController();

    renderDropdownMessage("Searching…");

    try {
      const params = new URLSearchParams({
        q: query,
        type: config.type,
      });
      const response = await fetch(`${config.searchUrl}?${params}`, {
        signal: activeController.signal,
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      const data = await response.json().catch(() => null);
      if (seq !== requestSeq) return;

      if (!response.ok || !data) {
        renderDropdownMessage("Search unavailable");
        return;
      }

      const results = (data.results || [])
        .filter((row) => row.asset_type === config.type)
        .slice(0, MARKET_SEARCH_LIMIT);
      renderDropdownResults(results);
    } catch (err) {
      if (err.name === "AbortError") return;
      if (seq !== requestSeq) return;
      renderDropdownMessage("Search unavailable");
    }
  }

  function onInputChange() {
    const query = input.value.trim();

    if (!query) {
      requestSeq += 1;
      if (activeController) {
        activeController.abort();
        activeController = null;
      }
      closeDropdown();
      return;
    }

    runSearch(query);
  }

  function go() {
    const query = input.value.trim();
    if (!query) return;

    const firstHit = dropdown.querySelector("a.market-search-hit");
    if (firstHit?.href) {
      window.location.assign(firstHit.href);
      return;
    }

    const path = assetPath(query);
    if (path) window.location.assign(path);
  }

  input.addEventListener("input", onInputChange);
  input.addEventListener("focus", () => {
    if (input.value.trim()) {
      onInputChange();
    }
  });

  button?.addEventListener("click", go);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      go();
    }
    if (e.key === "Escape") {
      closeDropdown();
    }
  });

  document.addEventListener("click", (e) => {
    if (!e.target.closest(".market-search-field")) {
      closeDropdown();
    }
  });

  if (config.appGameSelectId) {
    syncCustomAppIdField();
    document.getElementById(config.appGameSelectId)?.addEventListener("change", () => {
      syncCustomAppIdField();
      if (input.value.trim()) {
        onInputChange();
      }
    });
  }

  if (config.appIdInputId) {
    document.getElementById(config.appIdInputId)?.addEventListener("input", () => {
      if (input.value.trim()) {
        onInputChange();
      }
    });
  }

  if (config.appSelectId && !config.appGameSelectId && !config.appIdInputId) {
    document.getElementById(config.appSelectId)?.addEventListener("change", () => {
      if (input.value.trim()) {
        onInputChange();
      }
    });
  }
}
