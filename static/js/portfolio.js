/**
 * portfolio.js — страница детального просмотра актива.
 * Зависит от: chart_period.js (initPeriodLineChart), Chart.js
 */

"use strict";

function initPriceChart() {
  const canvas = document.getElementById("priceChart");
  if (!canvas) return;

  initPeriodLineChart({
    canvasId: "priceChart",
    dataElementId: "asset-chart-data",
    lineColor: canvas.dataset.lineColor || "#00e676",
    fillStart: canvas.dataset.fillStart || "rgba(0, 230, 118, 0.15)",
    fillEnd: canvas.dataset.fillEnd || "rgba(0, 230, 118, 0)",
    showLegend: true,
    datasetLabel: canvas.dataset.symbol || "Price",
    tension: 0.4,
    gradientHeight: 260,
    tickFontSize: 10,
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
              `  ${ctx.parsed.y >= 0 ? "+" : ""}${ctx.parsed.y}`,
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
            callback: (v) => `${v}`,
          },
        },
      },
    },
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initPriceChart();
  initPnlChart();
});
