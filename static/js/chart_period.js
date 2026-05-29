"use strict";

const CHART_PERIOD_LABELS = {
  7: "Last 7 days",
  30: "Last 30 days",
  365: "Last year",
  1825: "Last 5 years",
};

function chartPeriodLabel(timestamp) {
  const raw = (timestamp || "").slice(0, 10);
  const dt = new Date(`${raw}T00:00:00`);
  if (Number.isNaN(dt.getTime())) return raw;
  return dt.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "2-digit",
  });
}

function parseChartPeriodDate(timestamp) {
  return new Date(`${(timestamp || "").slice(0, 10)}T00:00:00`);
}

function filterChartPoints(points, days, cap) {
  if (!points.length) return [];
  const span = Math.min(days, cap);
  const lastDate = parseChartPeriodDate(points[points.length - 1].t);
  const cutoff = new Date(lastDate);
  cutoff.setDate(cutoff.getDate() - span);
  const filtered = points.filter(
    (point) => parseChartPeriodDate(point.t) >= cutoff,
  );
  return filtered.length ? filtered : points;
}

function chartSeriesFromPoints(points) {
  return {
    labels: points.map((point) => chartPeriodLabel(point.t)),
    values: points.map((point) => point.v),
  };
}

function chartPeriodSubtitle(days, periodCap) {
  const span = Math.min(days, periodCap);
  if (span === 365 && periodCap < 1825) {
    return "Last year (max range)";
  }
  return CHART_PERIOD_LABELS[days] || `Last ${days} days`;
}

function initChartPeriodToolbar({
  periodBar,
  points,
  periodCap,
  subtitleEl,
  onPeriodChange,
}) {
  if (!points?.length || !periodBar) return;

  periodBar.querySelectorAll(".chart-period-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      periodBar.querySelectorAll(".chart-period-btn").forEach((b) => {
        b.classList.remove("active");
      });
      btn.classList.add("active");

      const days = Number(btn.dataset.days);
      const sliced = filterChartPoints(points, days, periodCap);
      const next = chartSeriesFromPoints(sliced);
      onPeriodChange(next, days);

      if (subtitleEl) {
        subtitleEl.textContent = chartPeriodSubtitle(days, periodCap);
      }
    });
  });
}

/**
 * Line chart with 7D / 1M / 1Y / 5Y period toolbar.
 * Expects JSON in #dataElementId: { points: [{t, v}, ...] } or legacy {labels, values}.
 */
function initPeriodLineChart({
  canvasId,
  dataElementId = "portfolio-chart-data",
  lineColor = "#00e676",
  fillStart = "rgba(0,230,118,0.18)",
  fillEnd = "rgba(0,230,118,0)",
  showLegend = false,
  datasetLabel = "",
  tension = 0.25,
  gradientHeight = 280,
  formatY = (v) => `$${Number(v).toLocaleString()}`,
  formatTooltip = (c) => `  $${Number(c.parsed.y).toLocaleString()}`,
  maxTicksLimit = 7,
  tickFontSize = 11,
} = {}) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return null;

  const chartDataEl = document.getElementById(dataElementId);
  if (!chartDataEl) return null;

  const payload = JSON.parse(chartDataEl.textContent);
  const points = payload.points;
  const periodBar = document.querySelector(
    `.chart-period-toolbar[data-chart-id="${canvasId}"]`,
  );
  const periodCap = Number(periodBar?.dataset.periodCap || 1825);
  const subtitleEl = document.getElementById(`${canvasId}-subtitle`);
  const label = datasetLabel || canvas.dataset.symbol || "";

  let labels;
  let values;
  if (points?.length && periodBar) {
    const initialDays = Number(
      periodBar.querySelector(".chart-period-btn.active")?.dataset.days || "30",
    );
    ({ labels, values } = chartSeriesFromPoints(
      filterChartPoints(points, initialDays, periodCap),
    ));
  } else {
    labels = payload.labels || [];
    values = payload.values || [];
  }

  if (!values.length) return null;

  const ctx = canvas.getContext("2d");
  const gradient = ctx.createLinearGradient(0, 0, 0, gradientHeight);
  gradient.addColorStop(0, fillStart);
  gradient.addColorStop(1, fillEnd);

  const dataset = {
    data: values,
    borderColor: lineColor,
    borderWidth: 2,
    fill: true,
    backgroundColor: gradient,
    tension,
    pointRadius: 0,
    pointHoverRadius: 5,
    pointHoverBackgroundColor: lineColor,
    pointHoverBorderColor: "#0a0c0f",
  };
  if (label) dataset.label = label;

  const chart = new Chart(ctx, {
    type: "line",
    data: { labels, datasets: [dataset] },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: {
          display: showLegend,
          labels: showLegend
            ? {
                color: "#6b7280",
                font: { family: "DM Mono", size: 11 },
                boxWidth: 12,
                boxHeight: 2,
                useBorderRadius: true,
              }
            : undefined,
        },
        tooltip: {
          callbacks: { label: formatTooltip },
        },
      },
      scales: {
        x: {
          grid: { display: false },
          border: { display: false },
          ticks: {
            color: "#4b5563",
            font: { family: "DM Mono", size: tickFontSize },
            maxTicksLimit,
          },
        },
        y: {
          grid: { color: "rgba(255,255,255,0.04)" },
          border: { display: false },
          ticks: {
            color: "#4b5563",
            font: { family: "DM Mono", size: tickFontSize },
            callback: formatY,
          },
        },
      },
    },
  });

  if (subtitleEl && points?.length && periodBar) {
    const initialDays = Number(
      periodBar.querySelector(".chart-period-btn.active")?.dataset.days || "30",
    );
    subtitleEl.textContent = chartPeriodSubtitle(initialDays, periodCap);
  }

  initChartPeriodToolbar({
    periodBar,
    points,
    periodCap,
    subtitleEl,
    onPeriodChange: (next) => {
      chart.data.labels = next.labels;
      chart.data.datasets[0].data = next.values;
      chart.update();
    },
  });

  return chart;
}
