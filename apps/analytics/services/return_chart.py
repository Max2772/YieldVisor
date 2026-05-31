from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from apps.core.services.invest_api import InvestAPIClient, get_history
from apps.analytics.services.metrics import to_cumulative_pct
from apps.portfolio.models import Portfolio
from apps.portfolio.services.market_page import (
    _build_portfolio_chart,
    _contrib_by_day_sorted,
    _value_on_or_before,
)
from apps.portfolio.types import AssetType

BENCHMARK_TICKER = "SPY"
BENCHMARK_LABEL = "S&P 500"

SERIES_KEYS = ("all", AssetType.STOCK, AssetType.CRYPTO, AssetType.STEAM)
SERIES_META: dict[str, tuple[str, str]] = {
    "all": ("All", "#00e676"),
    AssetType.STOCK: ("Stocks & ETFs", "#4fc3f7"),
    AssetType.CRYPTO: ("Crypto", "#7c83ff"),
    AssetType.STEAM: ("Steam", "#ffb300"),
}


def _chart_to_pct_points(chart: dict[str, Any]) -> list[dict[str, Any]]:
    raw_points = chart.get("points") or []
    if len(raw_points) < 2:
        return []

    values = [float(point["v"]) for point in raw_points]
    pcts = to_cumulative_pct(values)
    return [
        {"t": point.get("t") or "", "v": pct}
        for point, pct in zip(raw_points, pcts)
    ]


def _history_fetch_days(portfolio_days: list[str], cap: int) -> int:
    if not portfolio_days:
        return cap
    try:
        first = date.fromisoformat(portfolio_days[0])
        last = date.fromisoformat(portfolio_days[-1])
        span = (last - first).days + 14
    except ValueError:
        span = cap
    return max(cap, span)


def _benchmark_pct_points(
    portfolio_timestamps: list[str],
    client: InvestAPIClient,
    *,
    fetch_days: int,
) -> list[dict[str, Any]]:
    """SPY cumulative return % on the same timestamps as the All series."""
    if len(portfolio_timestamps) < 2:
        return []

    portfolio_days = [timestamp[:10] for timestamp in portfolio_timestamps]
    request_days = _history_fetch_days(portfolio_days, fetch_days)

    history = get_history(
        AssetType.STOCK,
        BENCHMARK_TICKER,
        days=request_days,
        client=client,
    )
    if history is None or not history.points:
        return []

    spy_by_day = _contrib_by_day_sorted(Decimal("1"), list(history.points))
    if not spy_by_day:
        return []

    fallback_price = spy_by_day[0][1]
    values: list[float] = []
    for day in portfolio_days:
        price = _value_on_or_before(spy_by_day, day)
        values.append(price if price is not None else fallback_price)

    pcts = to_cumulative_pct(values)
    return [
        {"t": timestamp, "v": pct}
        for timestamp, pct in zip(portfolio_timestamps, pcts)
    ]


def build_return_chart(
    positions: list[Portfolio],
    client: InvestAPIClient,
    *,
    chart_period_cap: int,
) -> dict[str, Any]:
    """Cumulative return % series per asset type + S&P 500 benchmark for All."""
    groups: dict[str, list[Portfolio]] = {"all": positions}
    for asset_type in (AssetType.STOCK, AssetType.CRYPTO, AssetType.STEAM):
        subset = [position for position in positions if position.asset_type == asset_type]
        if subset:
            groups[asset_type] = subset

    series: dict[str, dict[str, Any]] = {}

    for key in SERIES_KEYS:
        subset = groups.get(key if key != "all" else "all")
        if not subset:
            continue
        chart = _build_portfolio_chart(
            subset,
            client,
            per_asset_max_range=True,
        )
        points = _chart_to_pct_points(chart)
        if len(points) < 2:
            continue
        label, color = SERIES_META[key]
        series[key] = {"label": label, "color": color, "points": points}

    benchmark: list[dict[str, Any]] = []
    all_points = series.get("all", {}).get("points") or []
    if all_points:
        benchmark = _benchmark_pct_points(
            [point["t"] for point in all_points],
            client,
            fetch_days=chart_period_cap,
        )

    return {
        "series": series,
        "benchmark": benchmark,
        "benchmark_label": BENCHMARK_LABEL,
        "filters": [
            {"key": key, "label": SERIES_META[key][0]}
            for key in SERIES_KEYS
            if key in series
        ],
    }