from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from django.conf import settings

from apps.core.services.invest_api import (
    InvestAPIError,
    PriceHistory,
    PriceQuote,
    get_history,
    get_quote,
    period_change_pct,
)
from apps.core.services.asset_display import asset_icon_context
from apps.core.services.ticker import format_change_delta, format_ticker_price
from apps.portfolio.types import AssetType


def _format_volume(volume: Decimal) -> str:
    value = float(volume)
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f}B"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}K"
    return f"{int(value)}"


def _chart_label(timestamp: str) -> str:
    raw = timestamp[:10] if timestamp else ""
    try:
        dt = datetime.fromisoformat(raw)
        return dt.strftime("%d %b")
    except ValueError:
        return raw


def _range_position(current: Decimal, low: Decimal, high: Decimal) -> int:
    if high <= low:
        return 50
    pct = ((current - low) / (high - low)) * 100
    return max(0, min(100, int(pct)))


def _fetch_quote_and_history(
    asset_type: str,
    asset_name: str,
    *,
    app_id: int | None,
    days: int,
) -> tuple[PriceQuote, PriceHistory | None] | None:
    quote = get_quote(asset_type, asset_name, app_id)
    if quote is None:
        return None
    try:
        history = get_history(asset_type, asset_name, app_id, days=days)
    except InvestAPIError:
        history = None
    return quote, history


def build_asset_detail_context(
    asset_type: str,
    asset_name: str,
    *,
    display_symbol: str,
    app_id: int | None = None,
    days: int | None = None,
    asset_type_label: str | None = None,
    hero_meta: str | None = None,
) -> dict[str, Any] | None:
    """
  Загружает котировку и историю из InvestAPI.
  Возвращает None, если актив не найден (404).
  """
    history_days = days if days is not None else settings.TICKER_CHANGE_DAYS

    try:
        result = _fetch_quote_and_history(
            asset_type,
            asset_name,
            app_id=app_id,
            days=history_days,
        )
    except InvestAPIError:
        raise

    if result is None:
        return None

    quote, history = result
    points = history.points if history else ()

    change_pct: Decimal | None = period_change_pct(points) if points else None
    change_delta = ""
    change_positive = True
    if change_pct is not None:
        change_delta, change_positive = format_change_delta(change_pct)

    prices = [float(p.price) for p in points]
    labels = [_chart_label(p.timestamp) for p in points]

    period_low: Decimal | None = None
    period_high: Decimal | None = None
    if points:
        period_low = min(p.price for p in points)
        period_high = max(p.price for p in points)

    last_volume: str | None = None
    if points and points[-1].volume is not None:
        last_volume = _format_volume(points[-1].volume)

    display_name = quote.full_name or quote.name
    if asset_type == AssetType.CRYPTO and display_symbol.upper() != quote.name.upper():
        subtitle = quote.name
    else:
        subtitle = quote.name if display_name != quote.name else ""

    asset: dict[str, Any] = {
        "symbol": display_symbol,
        "name": display_name,
        "subtitle": subtitle,
        "current_price": format_ticker_price(quote.price).lstrip("$"),
        "currency": quote.currency,
        "source": quote.source or "—",
        "cached_at": quote.cached_at,
        "asset_type": asset_type_label or asset_type.title(),
        "change_delta": change_delta,
        "change_positive": change_positive,
        "app_id": quote.app_id or app_id,
        **asset_icon_context(
            asset_type,
            display_label=display_symbol,
            asset_name=asset_name,
            app_id=quote.app_id or app_id,
        ),
    }

    if period_low is not None and period_high is not None:
        asset["period_low"] = f"{period_low:,.2f}"
        asset["period_high"] = f"{period_high:,.2f}"
        asset["range_pct"] = _range_position(quote.price, period_low, period_high)

    return {
        "asset": asset,
        "hero_meta": hero_meta or "",
        "history_days": history_days,
        "last_volume": last_volume,
        "chart": {"labels": labels, "prices": prices},
    }
