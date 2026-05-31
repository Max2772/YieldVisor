from __future__ import annotations

from decimal import Decimal
from typing import Any

from apps.analytics.services.breakdown import build_asset_breakdown
from apps.analytics.services.metrics import (
    alpha_annualized,
    annualized_volatility,
    beta,
    daily_returns,
    format_day_label,
    max_drawdown,
    monthly_returns,
    notable_days,
    sharpe_ratio,
)
from apps.analytics.services.return_chart import build_return_chart
from apps.analytics.services.risk_display import (
    build_risk_metrics,
    period_change_badge,
    sharpe_badge,
    volatility_badge,
)
from apps.core.market_catalog import (
    PORTFOLIO_CHART_MAX_DAYS,
    PORTFOLIO_CHART_MAX_DAYS_CRYPTO,
)
from apps.core.services.invest_api import InvestAPIClient
from apps.portfolio.models import Portfolio
from apps.portfolio.services.holdings import (
    _fetch_market_data,
    _format_value_short,
    format_pnl_pct,
)
from apps.portfolio.services.market_page import _build_portfolio_chart
from apps.portfolio.services.portfolio_overview import _build_type_allocation
from apps.portfolio.types import AssetType


def _empty_context() -> dict[str, Any]:
    return {
        "has_data": False,
        "total_return_pct": "0",
        "total_return_pos": True,
        "period_change_badge": None,
        "period_change_positive": True,
        "sharpe": "—",
        "sharpe_badge": "Add holdings to calculate",
        "max_drawdown": "0",
        "max_drawdown_badge": None,
        "volatility": "—",
        "volatility_badge": None,
        "return_chart": {"series": {}, "benchmark": [], "filters": []},
        "chart_period_cap": PORTFOLIO_CHART_MAX_DAYS,
        "monthly_chart": {"labels": [], "values": []},
        "asset_breakdown": [],
        "total_value_short": "0",
        "allocation": [],
        "risk_metrics": [],
        "best_day_pct": None,
        "best_day_date": None,
        "best_day_val": None,
        "worst_day_pct": None,
        "worst_day_date": None,
        "worst_day_val": None,
        "win_rate": None,
    }


def _portfolio_totals(
    positions: list[Portfolio],
    market_rows: list[tuple[Any, ...]],
) -> tuple[Decimal, Decimal, dict[str, Decimal]]:
    total_value = Decimal("0")
    cost_basis = Decimal("0")
    totals_by_type: dict[str, Decimal] = {
        AssetType.STOCK: Decimal("0"),
        AssetType.CRYPTO: Decimal("0"),
        AssetType.STEAM: Decimal("0"),
    }

    for position, price, *_rest in market_rows:
        cost_basis += position.cost_basis()
        if price is None:
            continue
        value = position.current_value(price)
        total_value += value
        totals_by_type[position.asset_type] += value

    return total_value, cost_basis, totals_by_type


def _insufficient_history_context(
    *,
    total_value: Decimal,
    cost_basis: Decimal,
    totals_by_type: dict[str, Decimal],
    market_rows: list[tuple[Any, ...]],
    positions: list[Portfolio],
    chart_period_cap: int,
) -> dict[str, Any]:
    total_pnl_pct = Decimal("0")
    if cost_basis > 0:
        total_pnl_pct = ((total_value - cost_basis) / cost_basis) * Decimal("100")

    allocation = [
        {"name": item["label"], "pct": item["pct"], "color": item["color"]}
        for item in _build_type_allocation(totals_by_type, total_value)
    ]

    return {
        "has_data": total_value > 0,
        "total_return_pct": format_pnl_pct(total_pnl_pct),
        "total_return_pos": total_pnl_pct >= 0,
        "period_change_badge": None,
        "period_change_positive": True,
        "sharpe": "—",
        "sharpe_badge": "Insufficient history",
        "max_drawdown": "0",
        "max_drawdown_badge": None,
        "volatility": "—",
        "volatility_badge": None,
        "return_chart": {"series": {}, "benchmark": [], "filters": []},
        "chart_period_cap": chart_period_cap,
        "monthly_chart": {"labels": [], "values": []},
        "asset_breakdown": build_asset_breakdown(positions, market_rows, total_value),
        "total_value_short": _format_value_short(total_value),
        "allocation": allocation,
        "risk_metrics": [],
        "best_day_pct": None,
        "best_day_date": None,
        "best_day_val": None,
        "worst_day_pct": None,
        "worst_day_date": None,
        "worst_day_val": None,
        "win_rate": None,
    }


def build_analytics_context(user) -> dict[str, Any]:
    positions = list(Portfolio.objects.filter(user=user).order_by("asset_type", "asset_name"))
    if not positions:
        return _empty_context()

    market_rows = _fetch_market_data(positions)
    total_value, cost_basis, totals_by_type = _portfolio_totals(positions, market_rows)

    has_crypto = any(position.asset_type == AssetType.CRYPTO for position in positions)
    chart_period_cap = (
        PORTFOLIO_CHART_MAX_DAYS_CRYPTO if has_crypto else PORTFOLIO_CHART_MAX_DAYS
    )

    with InvestAPIClient() as client:
        portfolio_chart = _build_portfolio_chart(
            positions,
            client,
            per_asset_max_range=True,
        )
        return_chart = build_return_chart(
            positions,
            client,
            chart_period_cap=chart_period_cap,
        )

    chart_points = portfolio_chart.get("points") or []
    days = [(point.get("t") or "")[:10] for point in chart_points]
    values = [float(point["v"]) for point in chart_points]

    total_pnl_pct = Decimal("0")
    if cost_basis > 0:
        total_pnl_pct = ((total_value - cost_basis) / cost_basis) * Decimal("100")

    allocation = [
        {"name": item["label"], "pct": item["pct"], "color": item["color"]}
        for item in _build_type_allocation(totals_by_type, total_value)
    ]

    if len(values) < 2:
        return _insufficient_history_context(
            total_value=total_value,
            cost_basis=cost_basis,
            totals_by_type=totals_by_type,
            market_rows=market_rows,
            positions=positions,
            chart_period_cap=chart_period_cap,
        )

    benchmark_values: list[float] = []
    bench_points = return_chart.get("benchmark") or []
    if bench_points and values:
        base = values[0]
        benchmark_values = [base * (1 + point["v"] / 100) for point in bench_points]

    portfolio_returns = daily_returns(values)
    benchmark_returns = daily_returns(benchmark_values) if benchmark_values else []

    max_dd, drawdown_day = max_drawdown(days, values)
    volatility = annualized_volatility(portfolio_returns)
    benchmark_volatility = annualized_volatility(benchmark_returns)
    sharpe = sharpe_ratio(portfolio_returns)
    beta_value = beta(portfolio_returns, benchmark_returns) if benchmark_returns else None
    alpha_value = (
        alpha_annualized(portfolio_returns, benchmark_returns, beta_value)
        if benchmark_returns
        else None
    )

    monthly_labels, monthly_values = monthly_returns(days, values)
    notable = notable_days(days, values)
    period_badge = period_change_badge(portfolio_chart, days=30, cap=chart_period_cap)

    drawdown_badge = f"⚠ {format_day_label(drawdown_day)} dip" if drawdown_day else None
    risk_metrics = build_risk_metrics(
        beta=beta_value,
        alpha=alpha_value,
        sharpe=sharpe,
        max_drawdown=max_dd,
        volatility=volatility,
    )

    return {
        "has_data": True,
        "total_return_pct": format_pnl_pct(total_pnl_pct),
        "total_return_pos": total_pnl_pct >= 0,
        "period_change_badge": period_badge[0] if period_badge else None,
        "period_change_positive": period_badge[1] if period_badge else True,
        "sharpe": f"{sharpe:.2f}" if sharpe is not None else "—",
        "sharpe_badge": sharpe_badge(sharpe),
        "max_drawdown": f"{max_dd:.1f}",
        "max_drawdown_badge": drawdown_badge,
        "volatility": f"{volatility:.1f}" if volatility is not None else "—",
        "volatility_badge": volatility_badge(volatility, benchmark_volatility),
        "return_chart": return_chart,
        "chart_period_cap": chart_period_cap,
        "monthly_chart": {"labels": monthly_labels, "values": monthly_values},
        "asset_breakdown": build_asset_breakdown(positions, market_rows, total_value),
        "total_value_short": _format_value_short(total_value),
        "allocation": allocation,
        "risk_metrics": risk_metrics or build_risk_metrics(
            beta=None,
            alpha=None,
            sharpe=None,
            max_drawdown=max_dd,
            volatility=volatility,
        ),
        **notable,
    }
