from __future__ import annotations

from decimal import Decimal
from typing import Any, TypedDict

from django.conf import settings
from django.core.cache import cache

from apps.core.market_catalog import (
    PORTFOLIO_CHART_DAYS,
    PORTFOLIO_CHART_MAX_DAYS,
    PORTFOLIO_CHART_MAX_DAYS_CRYPTO,
)
from apps.core.chart_colors import hero_chart_colors
from apps.core.services.asset_display import asset_icon_context
from apps.core.services.invest_api import InvestAPIClient, get_crypto_quotes, get_price
from apps.core.services.ticker import format_ticker_price
from apps.portfolio.models import Portfolio
from apps.portfolio.services.market_page import (
    _build_portfolio_chart,
    _fetch_market_result,
    _format_money,
    _split_money_display,
    slice_portfolio_chart_calendar_days,
)
from apps.portfolio.services.portfolio_overview import _chart_period_change
from apps.portfolio.types import AssetType

HERO_MOCKUP_CACHE_KEY = "main.hero_mockup"
HERO_MOCKUP_CACHE_TTL = int(
    getattr(settings, "HERO_MOCKUP_CACHE_TTL", settings.INVEST_API_CACHE_TTL)
)

HERO_QUANTITY = Decimal("1")
HERO_STEAM_NAME = "AK-47 | Redline (Field-Tested)"
HERO_STEAM_APP_ID = 730


class HeroAssetSpec(TypedDict):
    asset_type: str
    asset_name: str
    symbol: str
    app_id: int | None


def _hero_assets() -> list[HeroAssetSpec]:
    """Фиксированный демо-портфель: stock → crypto → steam."""
    return [
        {
            "asset_type": AssetType.STOCK,
            "asset_name": "NVDA",
            "symbol": "NVDA",
            "app_id": None,
        },
        {
            "asset_type": AssetType.CRYPTO,
            "asset_name": "bitcoin",
            "symbol": "BTC",
            "app_id": None,
        },
        {
            "asset_type": AssetType.STEAM,
            "asset_name": HERO_STEAM_NAME,
            "symbol": HERO_STEAM_NAME,
            "app_id": HERO_STEAM_APP_ID,
        },
    ]


def _demo_position(spec: HeroAssetSpec) -> Portfolio:
    return Portfolio(
        user_id=1,
        asset_type=spec["asset_type"],
        asset_name=spec["asset_name"],
        quantity=HERO_QUANTITY,
        avg_buy_price=Decimal("0"),
        app_id=spec.get("app_id"),
    )


def _fetch_hero_price(
    spec: HeroAssetSpec,
    client: InvestAPIClient,
    *,
    crypto_quotes: dict[str, Any],
) -> Decimal | None:
    if spec["asset_type"] == AssetType.CRYPTO:
        quote = crypto_quotes.get(spec["asset_name"].strip().lower())
        if quote:
            return quote.price
    try:
        return get_price(
            spec["asset_type"],
            spec["asset_name"],
            spec.get("app_id"),
            client=client,
        )
    except Exception:
        return None


def _chart_period_delta(chart: dict[str, Any]) -> tuple[str, bool] | None:
    values = chart.get("values") or []
    if len(values) < 2:
        return None
    delta = Decimal(str(values[-1])) - Decimal(str(values[0]))
    return _format_money(abs(delta)), delta >= 0


def _empty_context(*, chart_period_cap: int) -> dict[str, Any]:
    return {
        "has_data": False,
        "total_value_dollars": "—",
        "total_value_cents": "—",
        "value_change": None,
        "value_change_positive": True,
        "period_pnl": "—",
        "period_pnl_positive": True,
        "assets": [],
        "hero_chart": {"labels": [], "values": [], "points": []},
        "chart_period_cap": chart_period_cap,
        **hero_chart_colors(),
    }


def _build_hero_mockup_context() -> dict[str, Any]:
    hero_assets = _hero_assets()
    has_crypto = any(spec["asset_type"] == AssetType.CRYPTO for spec in hero_assets)
    chart_period_cap = (
        PORTFOLIO_CHART_MAX_DAYS_CRYPTO if has_crypto else PORTFOLIO_CHART_MAX_DAYS
    )
    empty = _empty_context(chart_period_cap=chart_period_cap)

    with InvestAPIClient() as client:
        crypto_quotes = get_crypto_quotes(
            [
                spec["asset_name"]
                for spec in hero_assets
                if spec["asset_type"] == AssetType.CRYPTO
            ],
            client=client,
        )

        prices: dict[str, Decimal] = {}
        for spec in hero_assets:
            price = _fetch_hero_price(spec, client, crypto_quotes=crypto_quotes)
            if price is not None and price > 0:
                prices[spec["symbol"]] = price

        if len(prices) != len(hero_assets):
            return empty

        positions = [_demo_position(spec) for spec in hero_assets]

        portfolio_chart = _build_portfolio_chart(
            positions,
            client,
            per_asset_max_range=True,
        )
        if not portfolio_chart.get("values"):
            return empty

        sliced_chart = slice_portfolio_chart_calendar_days(
            portfolio_chart,
            days=PORTFOLIO_CHART_DAYS,
            cap=chart_period_cap,
        )

        total_value = sum(prices[spec["symbol"]] for spec in hero_assets)
        dollars, cents = _split_money_display(total_value)

        value_change = None
        value_change_positive = True
        period_pnl = "—"
        period_pnl_positive = True
        if period := _chart_period_change(sliced_chart):
            value_change, value_change_positive = period
        if delta := _chart_period_delta(sliced_chart):
            period_pnl, period_pnl_positive = delta

        assets: list[dict[str, Any]] = []
        for spec in hero_assets:
            icon = asset_icon_context(
                spec["asset_type"],
                display_label=spec["symbol"],
                asset_name=spec["asset_name"],
                app_id=spec.get("app_id"),
                crypto_symbol=spec["symbol"]
                if spec["asset_type"] == AssetType.CRYPTO
                else None,
            )
            market_row = _fetch_market_result(
                spec["asset_type"],
                spec["asset_name"],
                app_id=spec.get("app_id"),
                symbol=spec["symbol"],
                client=client,
            )
            price = prices[spec["symbol"]]
            assets.append({
                **icon,
                "asset_type": spec["asset_type"],
                "ticker": spec["symbol"],
                "price": market_row["price"] if market_row else format_ticker_price(price).lstrip("$"),
                "change_pct": market_row["change"] if market_row else "—",
                "change_positive": market_row["pos"] if market_row else True,
            })

    return {
        "has_data": True,
        "total_value_dollars": dollars,
        "total_value_cents": cents,
        "value_change": value_change,
        "value_change_positive": value_change_positive,
        "period_pnl": period_pnl,
        "period_pnl_positive": period_pnl_positive,
        "assets": assets,
        "hero_chart": sliced_chart,
        "chart_period_cap": chart_period_cap,
        **hero_chart_colors(),
    }


def build_hero_mockup_context(*, use_cache: bool = True) -> dict[str, Any]:
    if use_cache:
        cached = cache.get(HERO_MOCKUP_CACHE_KEY)
        if cached is not None:
            return cached

    ctx = _build_hero_mockup_context()
    if use_cache and ctx.get("has_data"):
        cache.set(HERO_MOCKUP_CACHE_KEY, ctx, HERO_MOCKUP_CACHE_TTL)
    return ctx
