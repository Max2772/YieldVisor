from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.utils.timesince import timesince

from apps.alerts.models import Alert
from apps.core.chart_colors import portfolio_chart_colors
from apps.core.market_catalog import (
    PORTFOLIO_CHART_DAYS,
    PORTFOLIO_CHART_MAX_DAYS,
    PORTFOLIO_CHART_MAX_DAYS_CRYPTO,
)
from apps.core.services.invest_api import InvestAPIClient, get_price
from apps.core.services.ticker import format_ticker_price
from apps.portfolio.models import Portfolio
from apps.portfolio.services.holdings import (
    _build_item_row,
    _fetch_market_data,
    _format_money,
    _format_value_short,
    format_pnl_pct,
)
from apps.portfolio.services.market_page import (
    _build_portfolio_chart,
    _collect_cached_times,
    _compute_performers,
    _format_last_update,
    _split_money_display,
    slice_portfolio_chart_calendar_days,
)
from apps.portfolio.types import AssetType

TYPE_LABELS: dict[str, tuple[str, str]] = {
    AssetType.STOCK: ("Stocks", "#4fc3f7"),
    AssetType.CRYPTO: ("Crypto", "#7c83ff"),
    AssetType.STEAM: ("Steam", "#ffb300"),
}

ALERT_BAR_COLORS: dict[str, str] = {
    AssetType.STOCK: "var(--amber)",
    AssetType.CRYPTO: "var(--purple)",
    AssetType.STEAM: "#4fc3f7",
}


def _build_type_allocation(
    totals_by_type: dict[str, Decimal],
    total_value: Decimal,
) -> list[dict[str, Any]]:
    if total_value <= 0:
        return []

    ordered = sorted(
        totals_by_type.items(),
        key=lambda pair: pair[1],
        reverse=True,
    )
    allocation: list[dict[str, Any]] = []
    for index, (asset_type, amount) in enumerate(ordered):
        if amount <= 0:
            continue
        label, color = TYPE_LABELS.get(asset_type, (asset_type.title(), "#888"))
        pct = int((amount / total_value) * 100)
        allocation.append({
            "label": label,
            "pct": max(pct, 1),
            "color": color,
        })

    remainder = 100 - sum(item["pct"] for item in allocation)
    if remainder and allocation:
        allocation[0]["pct"] += remainder
    return allocation


def _pnl_pct_for(position: Portfolio, row: dict[str, Any]) -> Decimal | None:
    if row["market_price"] == "—":
        return None
    cost = position.cost_basis()
    if cost <= 0:
        return None
    try:
        market = Decimal(row["total"].replace(",", ""))
    except Exception:
        return None
    return ((market - cost) / cost) * Decimal("100")


def _to_portfolio_asset(position: Portfolio, row: dict[str, Any]) -> dict[str, Any]:
    pnl_pct = _pnl_pct_for(position, row)
    pct_display = format_pnl_pct(pnl_pct) if pnl_pct is not None else "—"
    sparkline = row.get("sparkline") or "0"
    return {
        "id": position.pk,
        "ticker": row["ticker"],
        "asset_type": position.asset_type,
        "app_name": row["meta"] if position.asset_type == AssetType.STEAM else "",
        "logo_url": row["logo_url"],
        "icon_text": row["icon_text"],
        "icon_bg": row["icon_bg"],
        "icon_fg": row["icon_fg"],
        "current_price": row["market_price"],
        "quantity": row["qty"],
        "current_value": row["total"],
        "pnl_pct": pct_display,
        "pnl_positive": row["pnl_pos"],
        "change_pct": row.get("change_pct", "—"),
        "change_positive": row.get("change_pos", True),
        "sparkline_values": sparkline.split(",") if sparkline else [],
        "sparkline_color": "#00e676" if row["pnl_pos"] else "#ff4d6d",
        "detail_url": row["detail_url"],
        "_pnl_pct": pnl_pct,
    }


def _chart_period_change(chart: dict[str, list[Any]]) -> tuple[str, bool] | None:
    values = chart.get("values") or []
    if len(values) < 2:
        return None
    first, last = Decimal(str(values[0])), Decimal(str(values[-1]))
    if first == 0:
        return None
    pct = ((last - first) / first) * Decimal("100")
    positive = pct >= 0
    sign = "+" if positive else "−"
    return f"{sign}{abs(pct):.2f}%", positive


def _alert_ticker(alert: Alert) -> str:
    if alert.asset_type == AssetType.STEAM:
        return alert.asset_name[:24]
    if alert.asset_type == AssetType.STOCK:
        return alert.asset_name.upper()
    return alert.asset_name.upper()


def _alert_progress(
    direction: str,
    current: Decimal,
    target: Decimal,
) -> int | None:
    if target <= 0:
        return None
    if direction in (">", ">="):
        return min(100, int((current / target) * 100))
    if current <= target:
        return 100
    return min(100, int((target / current) * 100))


def _build_alert_row(alert: Alert, current: Decimal | None) -> dict[str, Any]:
    ticker = _alert_ticker(alert)
    triggered = not alert.is_active and alert.triggered_at is not None

    row: dict[str, Any] = {
        "ticker": ticker,
        "condition": alert.direction,
        "target": _format_money(alert.target_price),
        "triggered": triggered,
        "meta": "—",
        "progress": None,
        "color": ALERT_BAR_COLORS.get(alert.asset_type, "var(--amber)"),
    }

    if triggered and alert.triggered_at:
        row["meta"] = f"Triggered · {timesince(alert.triggered_at)} ago"
        return row

    if current is None:
        row["meta"] = "Price unavailable"
        return row

    price_text = format_ticker_price(current).lstrip("$")
    progress = _alert_progress(alert.direction, current, alert.target_price)
    if progress is not None:
        row["progress"] = progress
        row["meta"] = f"Current: ${price_text} · {progress}% there"
    else:
        row["meta"] = f"Current: ${price_text}"

    return row


def _build_alerts(user) -> tuple[list[dict[str, Any]], int, int]:
    alerts_qs = (
        Alert.objects.filter(user=user, is_active=True)
        .order_by("-created_at")[:8]
    )

    rows: list[dict[str, Any]] = []
    near_target = 0

    with InvestAPIClient() as client:
        for alert in alerts_qs:
            price = get_price(
                alert.asset_type,
                alert.asset_name,
                alert.app_id,
                client=client,
            )
            row = _build_alert_row(alert, price)
            if alert.is_active and row.get("progress") is not None and row["progress"] >= 80:
                near_target += 1
            rows.append(row)

    active_count = Alert.objects.filter(user=user, is_active=True).count()
    return rows, active_count, near_target


def build_portfolio_overview_context(user) -> dict[str, Any]:
    positions = list(Portfolio.objects.filter(user=user).order_by("asset_type", "asset_name"))

    if not positions:
        return {
            "assets": [],
            "total_value": "0",
            "total_value_dollars": "0",
            "total_value_cents": "00",
            "total_value_short": "0",
            "total_pnl": "0",
            "total_pnl_pos": True,
            "total_pnl_pct": "0",
            "value_change": None,
            "value_change_positive": True,
            "alerts_count": 0,
            "alerts_near_target": 0,
            "assets_count": 0,
            "asset_types_count": 0,
            "portfolio_chart": {"labels": [], "values": [], "points": []},
            "chart_period_cap": PORTFOLIO_CHART_MAX_DAYS,
            "type_allocation": [],
            "alerts": [],
            "best_asset": "—",
            "worst_asset": "—",
            "last_updated": "—",
            **portfolio_chart_colors(),
        }

    market_rows = _fetch_market_data(positions)

    assets: list[dict[str, Any]] = []
    total_value = Decimal("0")
    total_pnl = Decimal("0")
    cost_basis = Decimal("0")
    totals_by_type: dict[str, Decimal] = {
        AssetType.STOCK: Decimal("0"),
        AssetType.CRYPTO: Decimal("0"),
        AssetType.STEAM: Decimal("0"),
    }
    cached_times: list[Any] = []

    for position, price, sparkline, full_name, crypto_symbol in market_rows:
        row = _build_item_row(position, price, sparkline, full_name, crypto_symbol)
        asset = _to_portfolio_asset(position, row)
        assets.append(asset)

        if price is not None:
            value = position.current_value(price)
            pnl = position.pnl(price)
            total_value += value
            total_pnl += pnl
            totals_by_type[position.asset_type] += value

        cost_basis += position.cost_basis()

    for asset in assets:
        asset.pop("_pnl_pct", None)

    type_allocation = _build_type_allocation(totals_by_type, total_value)

    has_crypto = any(p.asset_type == AssetType.CRYPTO for p in positions)
    chart_period_cap = (
        PORTFOLIO_CHART_MAX_DAYS_CRYPTO if has_crypto else PORTFOLIO_CHART_MAX_DAYS
    )

    with InvestAPIClient() as client:
        portfolio_chart = _build_portfolio_chart(
            positions,
            client,
            per_asset_max_range=True,
        )
        cached_times.extend(_collect_cached_times(positions, client))

    alerts, alerts_count, alerts_near = _build_alerts(user)

    best, worst = _compute_performers(
        positions,
        [
            {
                "ticker": asset["ticker"],
                "market_price": asset["current_price"],
                "total": asset["current_value"],
            }
            for asset in assets
        ],
    )

    pnl_pct = Decimal("0")
    if cost_basis > 0:
        pnl_pct = (total_pnl / cost_basis) * Decimal("100")

    dollars, cents = _split_money_display(total_value)
    period_change = _chart_period_change(
        slice_portfolio_chart_calendar_days(
            portfolio_chart,
            days=PORTFOLIO_CHART_DAYS,
            cap=chart_period_cap,
        ),
    )
    asset_types_count = sum(1 for amount in totals_by_type.values() if amount > 0)

    def format_performer(label: dict[str, str] | None) -> str:
        if not label:
            return "—"
        return f"{label['label']} {label['change']}"

    ctx: dict[str, Any] = {
        "assets": assets,
        "total_value": dollars,
        "total_value_dollars": dollars,
        "total_value_cents": cents,
        "total_value_short": _format_value_short(total_value),
        "total_pnl": _format_money(abs(total_pnl)),
        "total_pnl_pos": total_pnl >= 0,
        "total_pnl_pct": format_pnl_pct(pnl_pct),
        "alerts_count": alerts_count,
        "alerts_near_target": alerts_near,
        "assets_count": len(positions),
        "asset_types_count": asset_types_count,
        "portfolio_chart": portfolio_chart,
        "chart_period_cap": chart_period_cap,
        "type_allocation": type_allocation,
        "allocation": type_allocation,
        "alerts": alerts,
        "best_asset": format_performer(best),
        "worst_asset": format_performer(worst),
        "last_updated": _format_last_update(cached_times),
    }

    if period_change:
        ctx["value_change"], ctx["value_change_positive"] = period_change
    else:
        ctx["value_change"] = None
        ctx["value_change_positive"] = True

    ctx.update(portfolio_chart_colors())
    return ctx
