from __future__ import annotations

from decimal import Decimal
from typing import Any

from apps.analytics.services.metrics import metric_bar
from apps.portfolio.services.market_page import slice_portfolio_chart_calendar_days


def sharpe_badge(sharpe: Decimal | None) -> str:
    if sharpe is None:
        return "Insufficient history"
    if sharpe >= Decimal("1.5"):
        return "Excellent risk/reward"
    if sharpe >= Decimal("1"):
        return "Good risk/reward"
    if sharpe >= Decimal("0.5"):
        return "Moderate risk/reward"
    return "Low risk/reward"


def volatility_badge(
    portfolio_vol: Decimal | None,
    benchmark_vol: Decimal | None,
) -> str | None:
    if portfolio_vol is None or benchmark_vol is None:
        return None
    if portfolio_vol > benchmark_vol * Decimal("1.1"):
        return "Higher vs S&P 500"
    if portfolio_vol < benchmark_vol * Decimal("0.9"):
        return "Lower vs S&P 500"
    return "Similar to S&P 500"


def period_change_badge(
    chart: dict[str, Any],
    *,
    days: int,
    cap: int,
) -> tuple[str, bool] | None:
    sliced = slice_portfolio_chart_calendar_days(chart, days=days, cap=cap)
    values = sliced.get("values") or []
    if len(values) < 2 or values[0] == 0:
        return None
    first = Decimal(str(values[0]))
    last = Decimal(str(values[-1]))
    pct = ((last - first) / first) * Decimal("100")
    positive = pct >= 0
    sign = "+" if positive else "−"
    return f"{'▲' if positive else '▼'} vs last month {sign}{abs(pct):.1f}%", positive


def build_risk_metrics(
    *,
    beta: Decimal | None,
    alpha: Decimal | None,
    sharpe: Decimal | None,
    max_drawdown: Decimal,
    volatility: Decimal | None,
) -> list[dict[str, Any]]:
    metrics: list[dict[str, Any]] = []

    if beta is not None:
        metrics.append({
            "label": "Beta",
            "value": f"{beta:.2f}",
            "positive": False,
            "negative": False,
            "bar": metric_bar(float(beta), 2.0),
            "color": "#4fc3f7",
        })

    if alpha is not None:
        positive = alpha >= 0
        sign = "+" if positive else "−"
        metrics.append({
            "label": "Alpha (annualised)",
            "value": f"{sign}{abs(alpha):.1f}%",
            "positive": positive,
            "negative": not positive,
            "bar": metric_bar(float(alpha), 15.0),
            "color": "#00e676" if positive else "#ff4d6d",
        })

    if sharpe is not None:
        positive = sharpe >= 1
        metrics.append({
            "label": "Sharpe Ratio",
            "value": f"{sharpe:.2f}",
            "positive": positive,
            "negative": sharpe < 0,
            "bar": metric_bar(float(sharpe), 3.0),
            "color": "#00e676" if positive else "#ffb300",
        })

    metrics.append({
        "label": "Max Drawdown",
        "value": f"−{max_drawdown:.1f}%",
        "positive": False,
        "negative": True,
        "bar": metric_bar(float(max_drawdown), 30.0),
        "color": "#ff4d6d",
    })

    if volatility is not None:
        metrics.append({
            "label": "Volatility (30d)",
            "value": f"{volatility:.1f}%",
            "positive": False,
            "negative": False,
            "bar": metric_bar(float(volatility), 50.0),
            "color": "#ffb300",
        })

    return metrics
