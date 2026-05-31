from __future__ import annotations

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


def _benchmark_pct_points(
    portfolio_days: list[str],
    client: InvestAPIClient,
    *,
    fetch_days: int,
) -> list[dict[str, Any]]:
    if not portfolio_days:
        return []

    history = get_history(
        AssetType.STOCK,
        BENCHMARK_TICKER,
        days=fetch_days,
        client=client,
    )
    if history is None or not history.points:
        return []

    spy_by_day = _contrib_by_day_sorted(Decimal("1"), list(history.points))
    values: list[float] = []
    timestamps: list[str] = []
    for day in portfolio_days:
        price = _value_on_or_before(spy_by_day, day)
        if price is None:
            return []
        values.append(price)
        timestamps.append(f"{day}T00:00:00")

    pcts = to_cumulative_pct(values)
    return [{"t": ts, "v": pct} for ts, pct in zip(timestamps, pcts)]


def build_return_chart(
    positions: list[Portfolio],
    client: InvestAPIClient,
    *,
    chart_period_cap: int,
) -> dict[str, Any]:
    """Cumulative return % series per asset type + S&P 500 benchmark."""
    groups: dict[str, list[Portfolio]] = {"all": positions}
    for asset_type in (AssetType.STOCK, AssetType.CRYPTO, AssetType.STEAM):
        subset = [position for position in positions if position.asset_type == asset_type]
        if subset:
            groups[asset_type] = subset

    series: dict[str, dict[str, Any]] = {}
    master_days: list[str] = []

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
        if key == "all":
            master_days = [(point.get("t") or "")[:10] for point in chart.get("points") or []]

    benchmark: list[dict[str, Any]] = []
    if master_days:
        benchmark = _benchmark_pct_points(
            master_days,
            client,
            fetch_days=chart_period_cap,
        )

    return {
        "series": series,
        "benchmark": benchmark,
        "filters": [
            {"key": key, "label": SERIES_META[key][0]}
            for key in SERIES_KEYS
            if key in series
        ],
    }
