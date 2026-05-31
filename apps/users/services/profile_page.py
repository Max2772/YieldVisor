from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.core.cache import cache
from django.db.models import Count
from django.urls import reverse

from apps.alerts.models import Alert
from apps.history.models import History, HistoryOperation
from apps.portfolio.models import Portfolio
from apps.portfolio.services.holdings import (
    _fetch_quote_prices,
    _format_money,
    _format_qty,
    _format_value_short,
)
from apps.portfolio.services.market_page import _split_money_display
from apps.portfolio.types import AssetType
from apps.users.models import UserProfile

ACTIVITY_LIMIT = 20
SUMMARY_CACHE_TTL = 120


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


def _build_portfolio_summary(user) -> dict[str, Any]:
    cache_key = f"users.profile_summary.{user.pk}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    positions = list(Portfolio.objects.filter(user=user))
    assets_count = len(positions)
    alerts_count = Alert.objects.filter(user=user, is_active=True).count()

    if not positions:
        summary = {
            "total_value_short": "0",
            "total_value_dollars": "0",
            "total_value_cents": "00",
            "total_pnl": "0",
            "total_pnl_pos": True,
            "value_change": None,
            "value_change_positive": True,
            "alerts_count": alerts_count,
            "assets_count": 0,
        }
        cache.set(cache_key, summary, SUMMARY_CACHE_TTL)
        return summary

    total_value = Decimal("0")
    total_pnl = Decimal("0")

    for position, price in _fetch_quote_prices(positions):
        if price is None:
            continue
        total_value += position.current_value(price)
        total_pnl += position.pnl(price)

    dollars, cents = _split_money_display(total_value)
    summary = {
        "total_value_short": _format_value_short(total_value),
        "total_value_dollars": dollars,
        "total_value_cents": cents,
        "total_pnl": _format_money(abs(total_pnl)),
        "total_pnl_pos": total_pnl >= 0,
        "value_change": None,
        "value_change_positive": True,
        "alerts_count": alerts_count,
        "assets_count": assets_count,
    }
    cache.set(cache_key, summary, SUMMARY_CACHE_TTL)
    return summary


def invalidate_profile_summary_cache(user_id: int) -> None:
    cache.delete(f"users.profile_summary.{user_id}")


def build_profile_page_context(user) -> dict[str, Any]:
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
        **_build_portfolio_summary(user),
        "stocks_count": by_type.get(AssetType.STOCK, 0),
        "crypto_count": by_type.get(AssetType.CRYPTO, 0),
        "steam_count": by_type.get(AssetType.STEAM, 0),
    }
