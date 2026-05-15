/**
 * dashboard.js
 * ──────────────────────────────────────────────
 * JS только для страницы Dashboard.
 *
 * Зависит от: base.js (initSparkline, applyChartDefaults), Chart.js
 *
 * Содержит:
 *   - initPortfolioChart  — основной line chart динамики портфолио
 *   - initAllocationChart — donut chart по типам активов
 *   - initSparklines      — мини-графики в таблице активов
 *
 * В реальном Django-проекте данные для графиков
 * будут приходить из data-атрибутов или AJAX-эндпоинта:
 *   const data = JSON.parse(document.getElementById('chart-data').textContent);
 */

"use strict";

/* ── Portfolio line chart ─────────────────────────────────────────────── */
function initPortfolioChart() {
  const canvas = document.getElementById("portfolioChart");
  if (!canvas) return;

  const ctx = canvas.getContext("2d");

  // В Django: получить из data-атрибута или API
  // const raw = JSON.parse(canvas.dataset.values);
  const labels = buildDateLabels("2026-02-20", 28);
  const values = [
    12100, 12300, 11900, 12500, 12800, 12600, 13100, 13000,
    12700, 13200, 13600, 13400, 13800, 14200, 14000, 13700,
    13900, 14100, 14300, 14200, 14500, 14100, 14300, 14400,
    14100, 14200, 14256, 14256,
  ];

  const gradient = ctx.createLinearGradient(0, 0, 0, 280);
  gradient.addColorStop(0, "rgba(0, 230, 118, 0.18)");
  gradient.addColorStop(1, "rgba(0, 230, 118, 0)");

  new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          data: values,
          borderColor: "#00e676",
          borderWidth: 2,
          fill: true,
          backgroundColor: gradient,
          tension: 0.4,
          pointRadius: 0,
          pointHoverRadius: 5,
          pointHoverBackgroundColor: "#00e676",
          pointHoverBorderColor: "#0a0c0f",
          pointHoverBorderWidth: 2,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => `  $${ctx.parsed.y.toLocaleString()}`,
          },
        },
      },
      scales: {
        x: {
          grid: { display: false },
          border: { display: false },
          ticks: {
            color: "#4b5563",
            font: { family: "DM Mono", size: 11 },
            maxTicksLimit: 7,
          },
        },
        y: {
          grid: { color: "rgba(255,255,255,0.04)" },
          border: { display: false },
          ticks: {
            color: "#4b5563",
            font: { family: "DM Mono", size: 11 },
            callback: (v) => `$${(v / 1000).toFixed(0)}K`,
          },
        },
      },
    },
  });
}

/* ── Allocation donut chart ───────────────────────────────────────────── */
function initAllocationChart() {
  const canvas = document.getElementById("donutChart");
  if (!canvas) return;

  const ctx = canvas.getContext("2d");

  new Chart(ctx, {
    type: "doughnut",
    data: {
      datasets: [
        {
          data: [50, 29, 14, 7],
          backgroundColor: ["#4fc3f7", "#7c83ff", "#00e676", "#ffb300"],
          borderColor: "#111418",
          borderWidth: 3,
          hoverBorderWidth: 3,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "72%",
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => `  ${ctx.parsed}%`,
          },
        },
      },
    },
  });
}

/* ── Sparklines in assets table ───────────────────────────────────────── */
function initSparklines() {
  // initSparkline(id, data, color) — из base.js
  initSparkline("sp1", [710, 730, 780, 750, 800, 820, 874], "#00e676");
  initSparkline("sp2", [390, 400, 410, 395, 420, 408, 406], "#00e676");
  initSparkline("sp3", [2400, 2300, 2200, 2350, 2100, 2080, 2112], "#ff4d6d");
  initSparkline("sp4", [79000, 80500, 82000, 81000, 83500, 82800, 83200], "#00e676");
  initSparkline("sp5", [52, 50, 49, 48, 47, 48, 48.3], "#ff4d6d");
}

/* ── Helpers ─────────────────────────────────────────────────────────── */
/**
 * Генерирует массив читаемых дат, начиная с startDate.
 * @param {string} startDate  - формат "YYYY-MM-DD"
 * @param {number} count      - количество дней
 * @returns {string[]}
 */
function buildDateLabels(startDate, count) {
  const base = new Date(startDate);
  return Array.from({ length: count }, (_, i) => {
    const d = new Date(base);
    d.setDate(base.getDate() + i);
    return d.toLocaleDateString("en", { month: "short", day: "numeric" });
  });
}

/* ── Bootstrap ───────────────────────────────────────────────────────── */
document.addEventListener("DOMContentLoaded", () => {
  initPortfolioChart();
  initAllocationChart();
  initSparklines();
});
