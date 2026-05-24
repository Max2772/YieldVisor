from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import Any

from django.urls import reverse

from apps.core.async_utils import run_async
from apps.core.services.invest_api import InvestAPIClient, get_history, get_price
from apps.core.services.ticker import format_ticker_price
from apps.portfolio.models import Portfolio
from apps.portfolio.types import AssetType


def _format_money(value: Decimal) -> str:
    q = value.quantize(Decimal("0.01"))
    if q >= Decimal("1000"):
        return f"{q:,.2f}"
    return f"{q:.2f}"


def _format_qty(value: Decimal) -> str:
    q = value.normalize()
    text = format(q, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def _detail_url(position: Portfolio) -> str:
    if position.asset_type == AssetType.STOCK:
        return reverse("stocks:stock", kwargs={"ticker": position.asset_name.upper()})
    if position.asset_type == AssetType.CRYPTO:
        return reverse("crypto:coin", kwargs={"coin": position.asset_name})
    if position.asset_type == AssetType.STEAM and position.app_id:
        return reverse(
            "steam:item",
            kwargs={
                "app_id": position.app_id,
                "market_hash_name": position.asset_name,
            },
        )
    return "#"


def _icon_colors(asset_type: str) -> tuple[str, str]:
    if asset_type == AssetType.STOCK:
        return "#1a2e40", "#4fc3f7"
    if asset_type == AssetType.CRYPTO:
        return "#1a2a1a", "#00e676"
    return "#1a2040", "#7c83ff"


def _display_ticker(position: Portfolio) -> str:
    if position.asset_type == AssetType.STEAM:
        return position.asset_name[:20]
    return position.asset_name.upper()


def _sector_label(position: Portfolio) -> str:
    if position.asset_type == AssetType.STEAM and position.app_id:
        return f"App {position.app_id}"
    return "—"


async def _fetch_market_data(
    positions: list[Portfolio],
) -> list[tuple[Portfolio, Decimal | None, str]]:
    async with InvestAPIClient() as client:

        async def fetch_one(position: Portfolio) -> tuple[Portfolio, Decimal | None, str]:
            price = await get_price(
                position.asset_type,
                position.asset_name,
                position.app_id,
                client=client,
            )
            sparkline = ""
            if price is not None:
                try:
                    history = await get_history(
                        position.asset_type,
                        position.asset_name,
                        position.app_id,
                        days=7,
                        client=client,
                    )
                    if history and history.points:
                        sparkline = ",".join(str(float(p.price)) for p in history.points)
                except Exception:
                    pass
            return position, price, sparkline

        return list(await asyncio.gather(*[fetch_one(p) for p in positions]))


def _build_item_row(
    position: Portfolio,
    price: Decimal | None,
    sparkline: str,
) -> dict[str, Any]:
    icon_bg, icon_fg = _icon_colors(position.asset_type)
    ticker = _display_ticker(position)

    if price is None:
        return {
            "ticker": ticker,
            "name": position.asset_name,
            "detail_url": _detail_url(position),
            "sector": _sector_label(position),
            "avg_buy": _format_money(position.avg_buy_price),
            "market_price": "—",
            "pnl": "—",
            "pnl_pos": True,
            "qty": _format_qty(position.quantity),
            "total": _format_money(position.cost_basis()),
            "sparkline": "0",
            "icon_bg": icon_bg,
            "icon_fg": icon_fg,
        }

    pnl_value = position.pnl(price)
    total = position.current_value(price)
    return {
        "ticker": ticker,
        "name": position.asset_name,
        "detail_url": _detail_url(position),
        "sector": _sector_label(position),
        "avg_buy": _format_money(position.avg_buy_price),
        "market_price": format_ticker_price(price).lstrip("$"),
        "pnl": _format_money(abs(pnl_value)),
        "pnl_pos": pnl_value >= 0,
        "qty": _format_qty(position.quantity),
        "total": _format_money(total),
        "sparkline": sparkline or "0",
        "icon_bg": icon_bg,
        "icon_fg": icon_fg,
        "_total_raw": total,
        "_pnl_raw": pnl_value,
    }


def _empty_summary() -> dict[str, Any]:
    return {
        "portfolio_value": "0",
        "position_count": 0,
        "unrealised_pnl": "0",
        "pnl_pos": True,
        "pnl_pct": "0",
    }


def build_holdings(user, asset_type: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    positions = list(
        Portfolio.objects.filter(user=user, asset_type=asset_type).order_by("asset_name")
    )
    if not positions:
        return [], _empty_summary()

    market_rows = run_async(_fetch_market_data(positions))

    items: list[dict[str, Any]] = []
    total_value = Decimal("0")
    total_pnl = Decimal("0")
    cost_basis = Decimal("0")

    for position, price, sparkline in market_rows:
        row = _build_item_row(position, price, sparkline)
        items.append(row)
        if "_total_raw" in row:
            total_value += row["_total_raw"]
            total_pnl += row["_pnl_raw"]
            cost_basis += position.cost_basis()
        else:
            cost_basis += position.cost_basis()

    for row in items:
        row.pop("_total_raw", None)
        row.pop("_pnl_raw", None)

    pnl_pct = Decimal("0")
    if cost_basis > 0:
        pnl_pct = (total_pnl / cost_basis) * 100

    dollars, _cents = f"{total_value:,.2f}".split(".")

    return items, {
        "portfolio_value": dollars,
        "position_count": len(positions),
        "unrealised_pnl": _format_money(abs(total_pnl)),
        "pnl_pos": total_pnl >= 0,
        "pnl_pct": f"{pnl_pct:.1f}",
    }
