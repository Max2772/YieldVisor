from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from django.conf import settings

from apps.core.market_catalog import (
    PORTFOLIO_CHART_MAX_DAYS,
    PORTFOLIO_CHART_MAX_DAYS_CRYPTO,
)
from apps.core.services.invest_api import (
    InvestAPIError,
    PriceHistory,
    PriceHistoryPoint,
    PriceQuote,
    get_history,
    get_quote,
    period_change_pct,
)
from apps.core.services.asset_display import asset_icon_context
from apps.core.services.asset_logos import crypto_icon_slug
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


def _market_symbol(
    asset_type: str,
    asset_name: str,
    display_symbol: str,
) -> str:
    if asset_type == AssetType.CRYPTO:
        slug = crypto_icon_slug(asset_name)
        return slug.upper() if slug else display_symbol
    return display_symbol


def _hero_title(
    asset_type: str,
    display_name: str,
    display_symbol: str,
) -> str:
    if asset_type == AssetType.CRYPTO:
        return (display_name or display_symbol).upper()
    return display_name or display_symbol


def _hero_subtitle(
    asset_type: str,
    *,
    market_symbol: str,
    hero_meta: str,
    subtitle: str,
    display_symbol: str,
) -> str:
    if asset_type == AssetType.CRYPTO:
        return market_symbol
    if hero_meta:
        return hero_meta
    return subtitle


def _filter_points_last_days(
    points: tuple[PriceHistoryPoint, ...],
    days: int,
) -> tuple[PriceHistoryPoint, ...]:
    if len(points) < 2:
        return points
    last_raw = points[-1].timestamp[:10]
    try:
        last_d = date.fromisoformat(last_raw)
    except ValueError:
        return points
    cutoff = last_d - timedelta(days=days)
    filtered = tuple(
        p
        for p in points
        if date.fromisoformat(p.timestamp[:10]) >= cutoff
    )
    return filtered if len(filtered) >= 2 else points


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
    chart_period_cap = (
        PORTFOLIO_CHART_MAX_DAYS_CRYPTO
        if asset_type == AssetType.CRYPTO
        else PORTFOLIO_CHART_MAX_DAYS
    )
    fetch_days = max(history_days, chart_period_cap)

    try:
        result = _fetch_quote_and_history(
            asset_type,
            asset_name,
            app_id=app_id,
            days=fetch_days,
        )
    except InvestAPIError:
        raise

    if result is None:
        return None

    quote, history = result
    points = history.points if history else ()
    metrics_points = _filter_points_last_days(points, history_days)

    change_pct: Decimal | None = (
        period_change_pct(metrics_points) if metrics_points else None
    )
    change_delta = ""
    change_positive = True
    if change_pct is not None:
        change_delta, change_positive = format_change_delta(change_pct)

    chart_points = [{"t": p.timestamp, "v": float(p.price)} for p in points]

    period_low: Decimal | None = None
    period_high: Decimal | None = None
    if metrics_points:
        period_low = min(p.price for p in metrics_points)
        period_high = max(p.price for p in metrics_points)

    last_volume: str | None = None
    if points and points[-1].volume is not None:
        last_volume = _format_volume(points[-1].volume)

    display_name = quote.full_name or quote.name
    quote_symbol = quote.symbol or display_symbol

    market_symbol: str
    hero_title: str
    hero_subtitle: str
    subtitle: str = ""

    if asset_type == AssetType.CRYPTO:
        # Для crypto используем symbol из API (например BTC/ETH/BNB),
        # а не переданный из URL slug.
        market_symbol = quote_symbol.upper()
        hero_title = _hero_title(asset_type, display_name, market_symbol)
        hero_subtitle = _hero_subtitle(
            asset_type,
            market_symbol=market_symbol,
            hero_meta=hero_meta or "",
            subtitle="",
            display_symbol=market_symbol,
        )
    else:
        subtitle = quote.name if display_name != quote.name else ""
        if asset_type == AssetType.STOCK and subtitle.upper() == display_symbol.upper():
            subtitle = ""

        market_symbol = _market_symbol(asset_type, asset_name, display_symbol)
        hero_title = _hero_title(asset_type, display_name, display_symbol)
        hero_subtitle = _hero_subtitle(
            asset_type,
            market_symbol=market_symbol,
            hero_meta=hero_meta or "",
            subtitle=subtitle,
            display_symbol=display_symbol,
        )

    asset: dict[str, Any] = {
        "symbol": market_symbol if asset_type == AssetType.CRYPTO else display_symbol,
        "market_symbol": market_symbol,
        "name": display_name,
        "hero_title": hero_title,
        "hero_subtitle": hero_subtitle,
        "subtitle": subtitle,
        "current_price": format_ticker_price(quote.price).lstrip("$"),
        "price_raw": quote.price,
        "currency": quote.currency,
        "source": quote.source or "—",
        "cached_at": quote.cached_at,
        "asset_type": asset_type_label or asset_type.title(),
        "change_delta": change_delta,
        "change_positive": change_positive,
        "app_id": quote.app_id or app_id,
        "has_holding": False,
        "coin_name": quote.name if asset_type == AssetType.CRYPTO else "",
        **asset_icon_context(
            asset_type,
            display_label=market_symbol if asset_type == AssetType.CRYPTO else display_symbol,
            asset_name=asset_name,
            app_id=quote.app_id or app_id,
            crypto_symbol=quote.symbol if asset_type == AssetType.CRYPTO else None,
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
        "chart_period_cap": chart_period_cap,
        "last_volume": last_volume,
        "chart": {"points": chart_points},
    }
