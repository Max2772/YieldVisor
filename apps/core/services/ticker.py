from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import Any

from django.conf import settings

from apps.core.constants import HOMEPAGE_TICKERS, TickerSpec
from apps.core.async_utils import run_async
from apps.core.services.invest_api import (
    InvestAPIClient,
    InvestAPIError,
    get_history,
    get_price,
    period_change_pct,
)


def format_ticker_price(price: Decimal) -> str:
    """Формат цены для бегущей строки: $2.38, $215.33, $83,200."""
    value = price.quantize(Decimal("0.01"))
    if value >= Decimal("1000"):
        text = f"{value:,.0f}" if value == value.to_integral() else f"{value:,.2f}"
        return f"${text}"
    if value >= Decimal("1"):
        return f"${value:,.2f}"
    return f"${value:.2f}"


def format_change_delta(pct: Decimal) -> tuple[str, bool]:
    """Строка для UI: '+2.34%' / '0.96%' (знак — стрелка ▲/▼ в шаблоне)."""
    positive = pct >= 0
    value = abs(pct).quantize(Decimal("0.01"))
    if positive:
        return f"+{value}%", True
    return f"{value}%", False


async def _fetch_ticker_item(
    spec: TickerSpec,
    order: int,
    client: InvestAPIClient,
) -> dict[str, Any] | None:
    days = settings.TICKER_CHANGE_DAYS

    try:
        history = await get_history(
            spec["asset_type"],
            spec["asset_name"],
            spec.get("app_id"),
            days=days,
            client=client,
        )
    except InvestAPIError:
        history = None

    price: Decimal | None = None
    change_pct: Decimal | None = None

    if history and history.points:
        price = history.points[-1].price
        change_pct = period_change_pct(history.points)

    if price is None:
        try:
            price = await get_price(
                spec["asset_type"],
                spec["asset_name"],
                spec.get("app_id"),
                client=client,
            )
        except InvestAPIError:
            return None

    if price is None:
        return None

    item: dict[str, Any] = {
        "symbol": spec["symbol"],
        "price": format_ticker_price(price),
        "_order": order,
    }

    if change_pct is not None:
        delta, positive = format_change_delta(change_pct)
        item["delta"] = delta
        item["positive"] = positive
    else:
        item["live"] = True

    return item


async def build_ticker_items_async() -> list[dict[str, Any]]:
    """Параллельная загрузка через asyncio.gather и общую aiohttp-сессию."""
    async with InvestAPIClient() as client:
        results = await asyncio.gather(
            *[
                _fetch_ticker_item(spec, order, client)
                for order, spec in enumerate(HOMEPAGE_TICKERS)
            ],
            return_exceptions=True,
        )

    items: list[dict[str, Any]] = []
    for result in results:
        if isinstance(result, dict):
            items.append(result)

    items.sort(key=lambda x: x.pop("_order", 0))
    return items


def build_ticker_items() -> list[dict[str, Any]]:
    """
    Синхронная обёртка для Django views.
    Один event loop на загрузку всего тикера.
    """
    return run_async(build_ticker_items_async())
