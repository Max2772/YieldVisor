/**
 * base.js
 * ──────────────────────────────────────────────
 * Общая логика для всех страниц приложения.
 * Подключается в конце base_app.html через {% block base_scripts %}.
 *
 * Содержит:
 *   - TabGroup      — переключение .tab внутри .tabs
 *   - initSparkline — tiny canvas line chart без зависимостей
 */

"use strict";

/* ── Tab groups ──────────────────────────────────────────────────────── */
/**
 * Автоматически навешивает переключение active-класса
 * на все .tabs > .tab пары на странице.
 */
function initTabs() {
  document.querySelectorAll(".tabs").forEach((group) => {
    group.querySelectorAll(".tab").forEach((tab) => {
      tab.addEventListener("click", () => {
        group
          .querySelectorAll(".tab")
          .forEach((t) => t.classList.remove("active"));
        tab.classList.add("active");
      });
    });
  });
}

/* ── Sparklines ──────────────────────────────────────────────────────── */
/**
 * Рисует миниатюрный line chart в <canvas>.
 *
 * @param {string}   id     - id атрибут canvas-элемента
 * @param {number[]} data   - массив числовых значений
 * @param {string}   color  - CSS-цвет линии
 */
function initSparkline(id, data, color) {
  const canvas = document.getElementById(id);
  if (!canvas) return;

  const ctx = canvas.getContext("2d");
  const w = canvas.width;
  const h = canvas.height;

  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const step = w / (data.length - 1);

  ctx.clearRect(0, 0, w, h);
  ctx.beginPath();

  data.forEach((val, i) => {
    const x = i * step;
    const y = h - ((val - min) / range) * (h - 6) - 3;
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  });

  ctx.strokeStyle = color;
  ctx.lineWidth = 1.5;
  ctx.stroke();
}

/* ── Chart.js shared defaults ────────────────────────────────────────── */
/**
 * Применяет общие defaults для Chart.js,
 * чтобы не повторять их в каждом модуле.
 * Вызывается один раз после загрузки Chart.js.
 */
function applyChartDefaults() {
  if (typeof Chart === "undefined") return;

  Chart.defaults.color = "#6b7280";
  Chart.defaults.font.family = "DM Mono";

  // Shared tooltip style
  Chart.defaults.plugins.tooltip.backgroundColor = "#181c22";
  Chart.defaults.plugins.tooltip.borderColor = "rgba(255,255,255,0.08)";
  Chart.defaults.plugins.tooltip.borderWidth = 1;
  Chart.defaults.plugins.tooltip.titleColor = "#6b7280";
  Chart.defaults.plugins.tooltip.bodyColor = "#e8eaf0";
  Chart.defaults.plugins.tooltip.padding = 12;
  Chart.defaults.plugins.tooltip.bodyFont = { family: "DM Mono", size: 13 };
}

/* ── DOMContentLoaded bootstrap ──────────────────────────────────────── */
document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  applyChartDefaults();
});
