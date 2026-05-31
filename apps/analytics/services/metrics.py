from __future__ import annotations

import math
from datetime import datetime
from decimal import Decimal
from statistics import mean, pstdev
from typing import Any

from apps.portfolio.services.holdings import _format_money

RISK_FREE_RATE = Decimal("0.04")
MONTH_LABELS = (
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
)


def to_cumulative_pct(values: list[float]) -> list[float]:
    if not values:
        return []
    base = values[0]
    if base == 0:
        return [0.0] * len(values)
    return [round((value - base) / base * 100, 2) for value in values]


def daily_returns(values: list[float]) -> list[float]:
    returns: list[float] = []
    for index in range(1, len(values)):
        prev = values[index - 1]
        if prev == 0:
            continue
        returns.append((values[index] - prev) / prev)
    return returns


def format_day_label(day: str) -> str:
    try:
        dt = datetime.fromisoformat(day)
    except ValueError:
        return day
    return dt.strftime("%d %b %Y")


def metric_bar(value: float, scale: float) -> int:
    if scale <= 0:
        return 0
    return min(100, max(0, int(abs(value) / scale * 100)))


def annualized_volatility(daily_rets: list[float]) -> Decimal | None:
    window = daily_rets[-30:]
    if len(window) < 2:
        return None
    std = pstdev(window)
    return Decimal(str(round(std * math.sqrt(252) * 100, 1)))


def sharpe_ratio(daily_rets: list[float]) -> Decimal | None:
    if len(daily_rets) < 2:
        return None
    avg = mean(daily_rets)
    std = pstdev(daily_rets)
    if std == 0:
        return None
    daily_rf = float(RISK_FREE_RATE) / 252
    return Decimal(str(round((avg - daily_rf) / std * math.sqrt(252), 2)))


def max_drawdown(
    days: list[str],
    values: list[float],
) -> tuple[Decimal, str | None]:
    if len(values) < 2:
        return Decimal("0"), None

    peak = values[0]
    max_dd = 0.0
    trough_day: str | None = None

    for day, value in zip(days, values):
        if value > peak:
            peak = value
        if peak <= 0:
            continue
        drawdown = (peak - value) / peak
        if drawdown > max_dd:
            max_dd = drawdown
            trough_day = day

    return Decimal(str(round(max_dd * 100, 1))), trough_day


def _aligned_returns(
    portfolio_returns: list[float],
    benchmark_returns: list[float],
) -> tuple[list[float], list[float]] | None:
    length = min(len(portfolio_returns), len(benchmark_returns))
    if length < 2:
        return None
    return portfolio_returns[-length:], benchmark_returns[-length:]


def beta(
    portfolio_returns: list[float],
    benchmark_returns: list[float],
) -> Decimal | None:
    aligned = _aligned_returns(portfolio_returns, benchmark_returns)
    if aligned is None:
        return None
    port, bench = aligned
    bench_mean = mean(bench)
    port_mean = mean(port)
    variance = sum((value - bench_mean) ** 2 for value in bench) / len(bench)
    if variance == 0:
        return None
    covariance = sum(
        (port_value - port_mean) * (bench_value - bench_mean)
        for port_value, bench_value in zip(port, bench)
    ) / len(port)
    return Decimal(str(round(covariance / variance, 2)))


def alpha_annualized(
    portfolio_returns: list[float],
    benchmark_returns: list[float],
    beta_value: Decimal | None,
) -> Decimal | None:
    if beta_value is None or len(portfolio_returns) < 2:
        return None
    aligned = _aligned_returns(portfolio_returns, benchmark_returns)
    if aligned is None:
        return None
    port, bench = aligned
    port_annual = mean(port) * 252 * 100
    bench_annual = mean(bench) * 252 * 100
    rf_pct = float(RISK_FREE_RATE) * 100
    alpha = port_annual - (rf_pct + float(beta_value) * (bench_annual - rf_pct))
    return Decimal(str(round(alpha, 1)))


def notable_days(days: list[str], values: list[float]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "best_day_pct": None,
        "best_day_date": None,
        "best_day_val": None,
        "worst_day_pct": None,
        "worst_day_date": None,
        "worst_day_val": None,
        "win_rate": None,
    }
    if len(values) < 2:
        return result

    best_pct = None
    worst_pct = None
    best_meta: tuple[str, float] | None = None
    worst_meta: tuple[str, float] | None = None
    positive_days = 0
    total_days = 0

    for index in range(1, len(values)):
        prev = values[index - 1]
        if prev == 0:
            continue
        change_pct = (values[index] - prev) / prev * 100
        change_val = values[index] - prev
        total_days += 1
        if change_pct > 0:
            positive_days += 1
        if best_pct is None or change_pct > best_pct:
            best_pct = change_pct
            best_meta = (days[index], change_val)
        if worst_pct is None or change_pct < worst_pct:
            worst_pct = change_pct
            worst_meta = (days[index], change_val)

    if best_pct is not None and best_meta is not None:
        result["best_day_pct"] = f"{abs(best_pct):.1f}"
        result["best_day_date"] = format_day_label(best_meta[0])
        result["best_day_val"] = _format_money(Decimal(str(abs(best_meta[1]))))

    if worst_pct is not None and worst_meta is not None:
        result["worst_day_pct"] = f"{abs(worst_pct):.1f}"
        result["worst_day_date"] = format_day_label(worst_meta[0])
        result["worst_day_val"] = _format_money(Decimal(str(abs(worst_meta[1]))))

    if total_days:
        result["win_rate"] = int(positive_days / total_days * 100)

    return result


def _month_key(day: str) -> str:
    return day[:7]


def _month_label(month_key: str) -> str:
    try:
        _year, month = month_key.split("-")
        return MONTH_LABELS[int(month) - 1]
    except (ValueError, IndexError):
        return month_key


def monthly_returns(
    days: list[str],
    values: list[float],
    *,
    months: int = 12,
) -> tuple[list[str], list[float]]:
    if len(values) < 2:
        return [], []

    month_ends: dict[str, float] = {}
    for day, value in zip(days, values):
        month_ends[_month_key(day)] = value

    ordered_months = sorted(month_ends.keys())
    returns: list[tuple[str, float]] = []
    for index in range(1, len(ordered_months)):
        prev_value = month_ends[ordered_months[index - 1]]
        current_value = month_ends[ordered_months[index]]
        if prev_value == 0:
            continue
        pct = (current_value - prev_value) / prev_value * 100
        returns.append((ordered_months[index], round(pct, 1)))

    returns = returns[-months:]
    labels = [_month_label(month_key) for month_key, _ in returns]
    values_out = [value for _, value in returns]
    return labels, values_out
