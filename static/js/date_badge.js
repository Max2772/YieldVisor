/**
 * date_badge.js — локальное время пользователя в topbar (.date-badge).
 */
"use strict";

function formatLocalDateTime(date = new Date()) {
  const locale = navigator.language || document.documentElement.lang || "en";
  try {
    const parts = new Intl.DateTimeFormat(locale, {
      weekday: "short",
      day: "numeric",
      month: "long",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    }).formatToParts(date);

    const pick = (type) => parts.find((p) => p.type === type)?.value ?? "";
    const hour = pick("hour").padStart(2, "0");
    const minute = pick("minute").padStart(2, "0");
    return `${pick("weekday")}, ${pick("day")} ${pick("month")} ${pick("year")} · ${hour}:${minute}`;
  } catch {
    return date.toLocaleString(locale, {
      weekday: "short",
      day: "numeric",
      month: "long",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    });
  }
}

function initDateBadges() {
  const badges = document.querySelectorAll("[data-local-time]");
  if (!badges.length) return;

  const tick = () => {
    const label = formatLocalDateTime();
    badges.forEach((el) => {
      el.textContent = label;
    });
  };

  tick();
  window.setInterval(tick, 60_000);
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initDateBadges);
} else {
  initDateBadges();
}
