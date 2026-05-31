from __future__ import annotations

from typing import Any

from django.db.models import Count
from django.urls import reverse

from apps.alerts.models import Alert
from apps.history.models import History, HistoryOperation
from apps.portfolio.models import Portfolio
from apps.portfolio.services.holdings import _format_money, _format_qty
from apps.portfolio.services.portfolio_overview import build_portfolio_overview_context
from apps.portfolio.types import AssetType
from apps.users.models import UserProfile

ACTIVITY_LIMIT = 20


def _positions_by_type(user) -> dict[str, int]:
    rows = (
        Portfolio.objects.filter(user=user)
        .values("asset_type")
        .annotate(count=Count("id"))
    )
    return {row["asset_type"]: row["count"] for row in rows}


def _history_activity_row(tx: History) -> dict[str, Any]:
    total = tx.quantity * tx.price
    is_buy = tx.operation == HistoryOperation.BUY
    label = tx.asset_name.upper() if tx.asset_type != AssetType.STEAM else tx.asset_name
    verb = "Added" if is_buy else "Removed"
    preposition = "to" if is_buy else "from"
    return {
        "type": "buy" if is_buy else "sell",
        "title": f"{verb} {_format_qty(tx.quantity)} {label} {preposition} portfolio",
        "created_at": tx.created_at,
        "amount": f"+${_format_money(total)}" if is_buy else f"−${_format_money(total)}",
        "positive": is_buy,
    }


def _alert_activity_row(alert: Alert) -> dict[str, Any]:
    ticker = alert.asset_name.upper()
    if alert.asset_type == AssetType.STEAM:
        ticker = alert.asset_name
    return {
        "type": "alert",
        "title": f"Alert triggered: {ticker} {alert.direction} ${_format_money(alert.target_price)}",
        "created_at": alert.triggered_at,
        "amount": f"${_format_money(alert.target_price)}",
        "positive": True,
    }


def _recent_activity(user) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []

    for tx in History.objects.filter(user=user).order_by("-created_at")[:ACTIVITY_LIMIT]:
        events.append(_history_activity_row(tx))

    for alert in Alert.objects.filter(
        user=user,
        triggered_at__isnull=False,
    ).order_by("-triggered_at")[:ACTIVITY_LIMIT]:
        events.append(_alert_activity_row(alert))

    events.sort(key=lambda row: row["created_at"], reverse=True)
    return events[:ACTIVITY_LIMIT]


def build_profile_page_context(user) -> dict[str, Any]:
    portfolio = build_portfolio_overview_context(user)
    by_type = _positions_by_type(user)

    try:
        profile = user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=user)

    return {
        "profile": profile,
        "active_nav": "profile",
        "recent_activity": _recent_activity(user),
        "history_url": reverse("history:history"),
        "portfolio_url": reverse("portfolio:portfolio"),
        "total_value_short": portfolio.get("total_value_short", "0"),
        "total_value_dollars": portfolio.get("total_value_dollars", "0"),
        "total_value_cents": portfolio.get("total_value_cents", "00"),
        "total_pnl": portfolio.get("total_pnl", "0"),
        "total_pnl_pos": portfolio.get("total_pnl_pos", True),
        "value_change": portfolio.get("value_change"),
        "value_change_positive": portfolio.get("value_change_positive", True),
        "alerts_count": portfolio.get("alerts_count", 0),
        "assets_count": portfolio.get("assets_count", 0),
        "stocks_count": by_type.get(AssetType.STOCK, 0),
        "crypto_count": by_type.get(AssetType.CRYPTO, 0),
        "steam_count": by_type.get(AssetType.STEAM, 0),
    }
