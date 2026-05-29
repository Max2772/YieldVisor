from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from django.utils import timezone

from apps.alerts.models import Alert
from apps.core.services.asset_logos import crypto_icon_slug
from apps.core.services.invest_api import InvestAPIClient, PriceQuote, get_quote
from apps.core.services.ticker import format_ticker_price
from apps.portfolio.services.market_page import _detail_url_for
from apps.portfolio.types import AssetType

ALERT_BAR_COLORS: dict[str, str] = {
    AssetType.STOCK: "var(--amber)",
    AssetType.CRYPTO: "var(--purple)",
    AssetType.STEAM: "#4fc3f7",
}

NEAR_TARGET_PROGRESS = 90


@dataclass(frozen=True)
class _QuoteCacheKey:
    asset_type: str
    asset_name: str
    app_id: int | None


def _format_display_price(value: Decimal) -> str:
    return format_ticker_price(value).lstrip("$")


def _alert_progress(direction: str, current: Decimal, target: Decimal) -> int | None:
    if target <= 0:
        return None
    if direction in (">", ">="):
        return min(100, int((current / target) * 100))
    if current <= target:
        return 100
    return min(100, int((target / current) * 100))


def _above_target(direction: str, current: Decimal, target: Decimal) -> bool:
    if direction in (">", ">="):
        return current >= target
    return current <= target


def _fetch_quotes(alerts: list[Alert]) -> dict[_QuoteCacheKey, PriceQuote]:
    quotes: dict[_QuoteCacheKey, PriceQuote] = {}
    with InvestAPIClient() as client:
        for alert in alerts:
            key = _QuoteCacheKey(alert.asset_type, alert.asset_name, alert.app_id)
            if key in quotes:
                continue
            quote = get_quote(
                alert.asset_type,
                alert.asset_name,
                alert.app_id,
                client=client,
            )
            if quote is not None:
                quotes[key] = quote
    return quotes


def _quote_for_alert(alert: Alert, quotes: dict[_QuoteCacheKey, PriceQuote]) -> PriceQuote | None:
    key = _QuoteCacheKey(alert.asset_type, alert.asset_name, alert.app_id)
    return quotes.get(key)


def _alert_display_name(alert: Alert, quote: PriceQuote | None) -> str:
    if alert.asset_type == AssetType.STEAM:
        return alert.asset_name
    if alert.asset_type == AssetType.CRYPTO:
        if quote and quote.symbol:
            return quote.symbol.upper()
        slug = crypto_icon_slug(alert.asset_name)
        return slug.upper() if slug else alert.asset_name.upper()
    return alert.asset_name.upper()


def check_and_trigger_alerts(user) -> None:
    """Проверяет активные алерты через get_quote и деактивирует сработавшие."""
    active = list(Alert.objects.filter(user=user, is_active=True))
    if not active:
        return

    with InvestAPIClient() as client:
        for alert in active:
            quote = get_quote(
                alert.asset_type,
                alert.asset_name,
                alert.app_id,
                client=client,
            )
            if quote is not None and alert.is_triggered(quote.price):
                alert.trigger()


def create_alert(
    user,
    *,
    asset_type: str,
    asset_name: str,
    app_id: int | None,
    direction: str,
    target_price: Decimal,
) -> Alert:
    return Alert.objects.create(
        user=user,
        asset_type=asset_type,
        asset_name=asset_name,
        app_id=app_id,
        direction=direction,
        target_price=target_price,
    )


def _build_active_row(
    alert: Alert,
    current: Decimal | None,
    *,
    quote: PriceQuote | None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "pk": alert.pk,
        "display_name": _alert_display_name(alert, quote),
        "detail_url": _detail_url_for(alert.asset_type, alert.asset_name, alert.app_id),
        "asset_type": alert.asset_type,
        "direction": alert.direction,
        "target_price": _format_display_price(alert.target_price),
        "current_price": "—",
        "progress": 0,
        "color": ALERT_BAR_COLORS.get(alert.asset_type, "var(--amber)"),
        "above_target": False,
        "triggered": False,
        "created_at": alert.created_at,
    }

    if current is None:
        return row

    row["current_price"] = _format_display_price(current)
    row["above_target"] = _above_target(alert.direction, current, alert.target_price)
    progress = _alert_progress(alert.direction, current, alert.target_price)
    row["progress"] = progress if progress is not None else 0
    return row


def build_alerts_page_context(user) -> dict[str, Any]:
    check_and_trigger_alerts(user)

    today = timezone.localdate()
    active_qs = Alert.objects.filter(user=user, is_active=True).order_by("-created_at")
    active_alerts = list(active_qs)

    history_qs = (
        Alert.objects.filter(user=user, is_active=False, triggered_at__isnull=False)
        .order_by("-triggered_at")[:20]
    )
    history_alerts = list(history_qs)

    quote_alerts = active_alerts + history_alerts
    quotes = _fetch_quotes(quote_alerts)

    alerts: list[dict[str, Any]] = []
    for alert in active_alerts:
        quote = _quote_for_alert(alert, quotes)
        current = quote.price if quote else None
        alerts.append(_build_active_row(alert, current, quote=quote))

    near_alerts: list[dict[str, Any]] = []
    for alert, row in zip(active_alerts, alerts, strict=True):
        if row["progress"] >= NEAR_TARGET_PROGRESS:
            near_alerts.append(
                {
                    "display_name": row["display_name"],
                    "direction": alert.direction,
                    "target": row["target_price"],
                    "current": row["current_price"],
                    "progress": row["progress"],
                },
            )
    near_alerts.sort(key=lambda item: item["progress"], reverse=True)

    triggered_history: list[dict[str, Any]] = []
    for alert in history_alerts:
        quote = _quote_for_alert(alert, quotes)
        current = quote.price if quote else None
        triggered_history.append(
            {
                "display_name": _alert_display_name(alert, quote),
                "direction": alert.direction,
                "target": _format_display_price(alert.target_price),
                "triggered_at": alert.triggered_at,
                "triggered_price": (
                    _format_display_price(current)
                    if current is not None
                    else _format_display_price(alert.target_price)
                ),
            },
        )

    return {
        "active_count": active_qs.count(),
        "triggered_today": Alert.objects.filter(
            user=user,
            triggered_at__date=today,
        ).count(),
        "total_alerts": Alert.objects.filter(user=user).count(),
        "inactive_count": Alert.objects.filter(user=user, is_active=False).count(),
        "alerts": alerts,
        "triggered_history": triggered_history,
        "near_alerts": near_alerts[:5],
    }
