"use strict";

const RETURN_POS_COLOR = "#00e676";
const RETURN_NEG_COLOR = "#ff4d6d";
const RETURN_POS_FILL = "rgba(0,230,118,0.18)";
const RETURN_NEG_FILL = "rgba(255,77,109,0.18)";
const BENCHMARK_COLOR = "#4fc3f7";

function formatReturnTooltip(ctx) {
  const value = ctx.parsed.y;
  const sign = value >= 0 ? "+" : "";
  return `  ${ctx.dataset.label}: ${sign}${value.toFixed(1)}%`;
}

function signedReturnDataset(label, data, baseColor) {
  const color = baseColor || RETURN_POS_COLOR;

  return {
    label,
    data,
    borderWidth: 2,
    fill: true,
    tension: 0.4,
    pointRadius: 0,
    pointHoverRadius: 5,
    borderColor: color,
    backgroundColor: RETURN_POS_FILL,
    segment: {
      borderColor: (ctx) => (ctx.p1.parsed.y < 0 ? RETURN_NEG_COLOR : color),
      backgroundColor: (ctx) => (ctx.p1.parsed.y < 0 ? RETURN_NEG_FILL : fillForColor(color)),
    },
  };
}

function fillForColor(hexColor) {
  const map = {
    "#00e676": RETURN_POS_FILL,
    "#4fc3f7": "rgba(79,195,247,0.18)",
    "#7c83ff": "rgba(124,131,255,0.18)",
    "#ffb300": "rgba(255,179,0,0.18)",
  };
  return map[hexColor] || RETURN_POS_FILL;
}

function sliceReturnSeries(points, days, periodCap) {
  const filtered = filterChartPoints(
    (points || []).map((point) => ({ t: point.t, v: point.v })),
    days,
    periodCap,
  );
  const dates = new Set(filtered.map((point) => point.t));
  return (points || []).filter((point) => dates.has(point.t));
}

function initReturnTypeFilter({ filterBar, onChange }) {
  if (!filterBar) return;
  filterBar.querySelectorAll(".analytics-return-filter-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      filterBar.querySelectorAll(".analytics-return-filter-btn").forEach((item) => {
        item.classList.remove("active");
        item.setAttribute("aria-selected", "false");
      });
      btn.classList.add("active");
      btn.setAttribute("aria-selected", "true");
      onChange(btn.dataset.seriesKey);
    });
  });
}

function initAnalyticsReturnChart() {
  const canvas = document.getElementById("returnChart");
  const dataEl = document.getElementById("analytics-return-chart-data");
  if (!canvas || !dataEl) return;

  const payload = JSON.parse(dataEl.textContent);
  const seriesMap = payload.series || {};
  const benchmark = payload.benchmark || [];
  const filters = payload.filters || [];
  if (!filters.length) return;

  const periodBar = document.querySelector('.chart-period-toolbar[data-chart-id="returnChart"]');
  const filterBar = document.getElementById("returnChartTypeFilter");
  const periodCap = Number(periodBar?.dataset.periodCap || 1825);
  const subtitleEl = document.getElementById("returnChart-subtitle");

  let activeKey = filters[0]?.key || "all";
  let periodDays = Number(
    periodBar?.querySelector(".chart-period-btn.active")?.dataset.days || "30",
  );

  function buildDatasets(key, slicedPrimary, slicedBenchmark) {
    const meta = seriesMap[key];
    const datasets = [
      signedReturnDataset(meta.label, slicedPrimary.map((point) => point.v), meta.color),
    ];
    if (key === "all" && slicedBenchmark.length) {
      datasets.push({
        label: "S&P 500",
        data: slicedBenchmark.map((point) => point.v),
        borderColor: BENCHMARK_COLOR,
        borderWidth: 1.5,
        fill: false,
        borderDash: [4, 4],
        tension: 0.4,
        pointRadius: 0,
        pointHoverRadius: 5,
      });
    }
    return datasets;
  }

  function renderSeries(key, days) {
    const meta = seriesMap[key];
    if (!meta) return null;

    const slicedPrimary = sliceReturnSeries(meta.points, days, periodCap);
    if (!slicedPrimary.length) return null;

    const slicedBenchmark = key === "all"
      ? sliceReturnSeries(benchmark, days, periodCap)
      : [];

    return {
      labels: slicedPrimary.map((point) => chartPeriodLabel(point.t)),
      datasets: buildDatasets(key, slicedPrimary, slicedBenchmark),
    };
  }

  let current = renderSeries(activeKey, periodDays);
  if (!current) return;

  const chart = new Chart(canvas.getContext("2d"), {
    type: "line",
    data: current,
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
            boxWidth: 20,
            usePointStyle: true,
          },
        },
        tooltip: { callbacks: { label: formatReturnTooltip } },
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
            callback: (value) => `${value}%`,
          },
        },
      },
    },
  });

  function updateChart() {
    const next = renderSeries(activeKey, periodDays);
    if (!next) return;
    chart.data.labels = next.labels;
    chart.data.datasets = next.datasets;
    chart.update();
    if (subtitleEl && periodBar) {
      subtitleEl.textContent = chartPeriodSubtitle(periodDays, periodCap);
    }
  }

  if (subtitleEl && periodBar) {
    subtitleEl.textContent = chartPeriodSubtitle(periodDays, periodCap);
  }

  initReturnTypeFilter({
    filterBar,
    onChange: (key) => {
      activeKey = key;
      updateChart();
    },
  });

  if (periodBar) {
    periodBar.querySelectorAll(".chart-period-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        periodBar.querySelectorAll(".chart-period-btn").forEach((item) => {
          item.classList.remove("active");
        });
        btn.classList.add("active");
        periodDays = Number(btn.dataset.days);
        updateChart();
      });
    });
  }
}

function initAnalyticsMonthlyChart() {
  const canvas = document.getElementById("monthlyChart");
  const dataEl = document.getElementById("analytics-monthly-chart-data");
  if (!canvas || !dataEl) return;

  const payload = JSON.parse(dataEl.textContent);
  const vals = payload.values || [];
  const labels = payload.labels || [];
  if (!vals.length) return;

  new Chart(canvas.getContext("2d"), {
    type: "bar",
    data: {
      labels,
      datasets: [{
        data: vals,
        backgroundColor: vals.map((value) =>
          value >= 0 ? "rgba(0,230,118,0.7)" : "rgba(255,77,109,0.7)",
        ),
        borderColor: vals.map((value) => (value >= 0 ? RETURN_POS_COLOR : RETURN_NEG_COLOR)),
        borderWidth: 1,
        borderRadius: 4,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => `  ${ctx.parsed.y > 0 ? "+" : ""}${ctx.parsed.y}%`,
          },
        },
      },
      scales: {
        x: {
          grid: { display: false },
          border: { display: false },
          ticks: { color: "#4b5563", font: { family: "DM Mono", size: 11 } },
        },
        y: {
          grid: { color: "rgba(255,255,255,0.04)" },
          border: { display: false },
          ticks: {
            color: "#4b5563",
            font: { family: "DM Mono", size: 11 },
            callback: (value) => `${value}%`,
          },
        },
      },
    },
  });
}

function initAnalyticsDonutChart() {
  const canvas = document.getElementById("donutChart");
  const dataEl = document.getElementById("analytics-allocation-data");
  if (!canvas || !dataEl) return;

  const slices = JSON.parse(dataEl.textContent);
  if (!slices.length) return;

  new Chart(canvas.getContext("2d"), {
    type: "doughnut",
    data: {
      datasets: [{
        data: slices.map((slice) => slice.pct),
        backgroundColor: slices.map((slice) => slice.color),
        borderColor: "#111418",
        borderWidth: 3,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "72%",
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: (ctx) => `  ${ctx.parsed}%` } },
      },
    },
  });
}

document.addEventListener("DOMContentLoaded", () => {
  initAnalyticsReturnChart();
  initAnalyticsMonthlyChart();
  initAnalyticsDonutChart();
});
