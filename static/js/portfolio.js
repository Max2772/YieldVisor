/**
 * portfolio.js
 * ──────────────────────────────────────────────
 * JS только для страницы детального просмотра актива.
 *
 * Зависит от: base.js (applyChartDefaults), Chart.js
 *
 * Содержит:
 *   - initPriceChart — line chart цены актива + avg buy line
 *   - initPnlChart   — bar chart P&L по периодам
 */

"use strict";

/* ── Price history chart ─────────────────────────────────────────────── */
function initPriceChart() {
  const canvas = document.getElementById("priceChart");
  if (!canvas) return;

  const ctx = canvas.getContext("2d");

  const chartEl = document.getElementById("asset-chart-data");
  let dates;
  let prices;
  const avgBuy = [];

  if (chartEl) {
    const payload = JSON.parse(chartEl.textContent);
    prices = payload.prices || [];
    dates = payload.labels || [];
  } else {
    dates = buildDateLabels("2026-02-20", 28);
    const offsets = [0,12,-8,20,15,5,25,18,-5,30,35,22,40,50,42,38,45,55,60,52,70,58,65,75,68,80,74,76];
    prices = offsets.map((v) => +(710 + v * 1.4).toFixed(2));
    avgBuy.push(...new Array(28).fill(714.18));
  }

  if (!prices.length) return;

  const symbol = canvas.dataset.symbol || "Price";

  const gradient = ctx.createLinearGradient(0, 0, 0, 240);
  gradient.addColorStop(0, "rgba(0, 230, 118, 0.15)");
  gradient.addColorStop(1, "rgba(0, 230, 118, 0)");

  new Chart(ctx, {
    type: "line",
    data: {
      labels: dates,
      datasets: [
        {
          label: symbol,
          data: prices,
          borderColor: "#00e676",
          borderWidth: 2,
          fill: true,
          backgroundColor: gradient,
          tension: 0.4,
          pointRadius: 0,
          pointHoverRadius: 5,
          pointHoverBackgroundColor: "#00e676",
          pointHoverBorderColor: "#0a0c0f",
        },
        ...(avgBuy.length
          ? [{
              label: "Avg Buy",
              data: avgBuy,
              borderColor: "rgba(255, 179, 0, 0.6)",
              borderWidth: 1.5,
              borderDash: [6, 3],
              fill: false,
              tension: 0,
              pointRadius: 0,
            }]
          : []),
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: {
          display: true,
          labels: {
            color: "#6b7280",
            font: { family: "DM Mono", size: 11 },
            boxWidth: 12,
            boxHeight: 2,
            useBorderRadius: true,
          },
        },
        tooltip: {
          callbacks: {
            label: (ctx) => `  $${ctx.parsed.y.toFixed(2)}`,
          },
        },
      },
      scales: {
        x: {
          grid: { display: false },
          border: { display: false },
          ticks: {
            color: "#4b5563",
            font: { family: "DM Mono", size: 10 },
            maxTicksLimit: 6,
          },
        },
        y: {
          grid: { color: "rgba(255,255,255,0.04)" },
          border: { display: false },
          ticks: {
            color: "#4b5563",
            font: { family: "DM Mono", size: 10 },
            callback: (v) => `$${v}`,
          },
        },
      },
    },
  });
}

/* ── P&L bar chart ───────────────────────────────────────────────────── */
function initPnlChart() {
  const canvas = document.getElementById("pnlChart");
  if (!canvas || !canvas.offsetParent) return;

  const ctx = canvas.getContext("2d");

  const labels = ["Feb 20", "Feb 24", "Feb 28", "Mar 4", "Mar 8", "Mar 12", "Mar 16"];
  const data   = [0, 50, -33, 84, 63, 160, 205];

  new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          data,
          backgroundColor: data.map((v) =>
            v >= 0 ? "rgba(0, 230, 118, 0.7)" : "rgba(255, 77, 109, 0.7)"
          ),
          borderRadius:  4,
          borderSkipped: false,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) =>
              `  ${ctx.parsed.y >= 0 ? "+" : ""}$${ctx.parsed.y}`,
          },
        },
      },
      scales: {
        x: {
          grid:   { display: false },
          border: { display: false },
          ticks:  { color: "#4b5563", font: { family: "DM Mono", size: 10 } },
        },
        y: {
          grid:   { color: "rgba(255,255,255,0.04)" },
          border: { display: false },
          ticks: {
            color:    "#4b5563",
            font:     { family: "DM Mono", size: 10 },
            callback: (v) => `$${v}`,
          },
        },
      },
    },
  });
}

/* ── Helpers ─────────────────────────────────────────────────────────── */
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
  initPriceChart();
  initPnlChart();
});
