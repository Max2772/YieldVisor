"""Help copy for Analytics page metrics (English)."""

from __future__ import annotations

METRIC_HELP: dict[str, str] = {
    "total_return": (
        "Unrealised gain or loss on your entire portfolio, expressed as a "
        "percentage of total cost basis (what you paid)."
    ),
    "sharpe": (
        "Risk-adjusted return: excess return per unit of volatility. "
        "Above 1.0 is generally good; above 1.5 is excellent."
    ),
    "max_drawdown": (
        "Largest peak-to-trough decline in portfolio value over the chart "
        "history — your worst drop from a recent high."
    ),
    "volatility": (
        "Annualised standard deviation of daily returns over the last 30 days. "
        "Higher values mean larger day-to-day swings."
    ),
    "cumulative_return": (
        "Portfolio performance over time, shown as cumulative % change from "
        "the start of the selected period. The benchmark line tracks the S&P 500."
    ),
    "monthly_returns": (
        "Month-over-month percentage change in portfolio value for the last "
        "12 months."
    ),
    "allocation": (
        "How your portfolio is divided across asset types — stocks, crypto, "
        "and Steam items — by current market value."
    ),
    "beta": (
        "Sensitivity to the S&P 500. Beta 1.0 moves with the market; "
        "above 1 is more volatile, below 1 is less."
    ),
    "alpha": (
        "Annualised excess return versus the S&P 500 after adjusting for "
        "market risk (beta). Positive alpha means risk-adjusted outperformance."
    ),
    "notable_days": (
        "Single best and worst daily moves, plus the share of trading days "
        "with a positive return."
    ),
    "risk_metrics": (
        "Key risk and reward measures derived from your portfolio's daily "
        "price history versus the S&P 500 benchmark."
    ),
}
