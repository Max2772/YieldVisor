/**
 * market_search.js — переход на страницу актива из Market Search.
 *
 * initMarketSearch({ type, baseUrl, appSelectId? })
 *   type: "stock" | "crypto" | "steam"
 *   baseUrl: префикс списка, напр. "/stocks/"
 */
"use strict";

function initMarketSearch(config) {
  const input = document.getElementById("marketSearchInput");
  const button = document.getElementById("marketSearchBtn");
  if (!input || !config?.baseUrl) return;

  const baseUrl = config.baseUrl.endsWith("/")
    ? config.baseUrl
    : `${config.baseUrl}/`;

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
      const select = config.appSelectId
        ? document.getElementById(config.appSelectId)
        : null;
      const appId = (select?.value || "730").trim();
      return `${baseUrl}${appId}/${encodeURIComponent(q)}/`;
    }
    return null;
  }

  function go() {
    const path = assetPath(input.value);
    if (path) window.location.assign(path);
  }

  button?.addEventListener("click", go);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      go();
    }
  });
}
