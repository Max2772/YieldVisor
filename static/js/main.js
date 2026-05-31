/**
 * landing.js
 * ──────────────────────────────────────────────
 * JS только для главной (публичной) страницы.
 *
 * Зависит от: base.js (загружается раньше), Chart.js
 *
 * Содержит:
 *   - initHeroChart  — мини-график в mockup-блоке
 */

"use strict";

/* ── Hero mini chart ─────────────────────────────────────────────────── */
function initHeroChart() {
  const canvas = document.getElementById("heroChart");
  if (!canvas) return;

  const chartDataEl = document.getElementById("hero-chart-data");
  const payload = chartDataEl ? JSON.parse(chartDataEl.textContent) : null;
  const values = payload?.values?.length
    ? payload.values
    : [
        11800, 12100, 11900, 12400, 12700, 12500, 13000, 12900,
        12600, 13100, 13500, 13400, 13800, 14200, 14000, 13800,
        14100, 14300, 14256,
      ];

  const ctx = canvas.getContext("2d");
  const lineColor = canvas.dataset.lineColor || "#00e676";
  const fillStart = canvas.dataset.fillStart || "rgba(0, 230, 118, 0.18)";
  const fillEnd = canvas.dataset.fillEnd || "rgba(0, 230, 118, 0)";

  const gradient = ctx.createLinearGradient(0, 0, 0, 130);
  gradient.addColorStop(0, fillStart);
  gradient.addColorStop(1, fillEnd);

  new Chart(ctx, {
    type: "line",
    data: {
      labels: values.map((_, i) => i),
      datasets: [
        {
          data: values,
          borderColor: lineColor,
          borderWidth: 2,
          fill: true,
          backgroundColor: gradient,
          tension: 0.4,
          pointRadius: 0,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { enabled: false },
      },
      scales: {
        x: { display: false },
        y: { display: false },
      },
    },
  });
}

/* ── Bootstrap ───────────────────────────────────────────────────────── */
document.addEventListener("DOMContentLoaded", () => {
  initHeroChart();
});
