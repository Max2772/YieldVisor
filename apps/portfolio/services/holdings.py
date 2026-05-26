from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from typing import Any

from django.urls import reverse

from apps.core.services.asset_display import asset_subtitle
from apps.core.services.invest_api import (
    InvestAPIClient,
    PriceHistory,
    PriceQuote,
    get_history,
    get_price,
    get_quote,
)
from apps.core.services.ticker import format_ticker_price
from apps.portfolio.models import Portfolio
from apps.portfolio.types import AssetType
from apps.steam.constants import steam_app_label

ALLOCATION_COLORS = (
    "#4fc3f7",
    "#00e676",
    "#ffb300",
    "#7c83ff",
    "#ff4d6d",
    "#e040fb",
    "#ff9100",
    "#69f0ae",
)


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
        return position.asset_name
    return position.asset_name.upper()


def _meta_label(position: Portfolio) -> str:
    if position.asset_type == AssetType.STEAM and position.app_id:
        return steam_app_label(position.app_id)
    return "—"


def _icon_text(position: Portfolio, ticker: str) -> str:
    if position.asset_type == AssetType.STEAM and position.app_id:
        label = steam_app_label(position.app_id)
        if label != "—":
            return label[:2]
    return ticker[:2].upper()


def _format_value_short(total_value: Decimal) -> str:
    if total_value >= Decimal("1000000"):
        return f"{total_value / Decimal('1000000'):.1f}M"
    if total_value >= Decimal("1000"):
        return f"{total_value / Decimal('1000'):.1f}K"
    return f"{total_value:.0f}"


def _build_value_allocation(
    items: list[dict[str, Any]],
    total_value: Decimal,
) -> list[dict[str, Any]]:
    """Доли портфеля по стоимости позиций (для donut chart)."""
    if total_value <= 0:
        return []

    valued = [
        (row["ticker"], row["_total_raw"])
        for row in items
        if row.get("_total_raw") is not None
    ]
    valued.sort(key=lambda pair: pair[1], reverse=True)
    if not valued:
        return []

    allocation: list[dict[str, Any]] = []
    for index, (label, amount) in enumerate(valued):
        pct = int((amount / total_value) * 100)
        allocation.append({
            "label": label,
            "pct": max(pct, 1) if amount > 0 else 0,
            "color": ALLOCATION_COLORS[index % len(ALLOCATION_COLORS)],
        })

    remainder = 100 - sum(slice_["pct"] for slice_ in allocation)
    if remainder and allocation:
        allocation[0]["pct"] += remainder

    return allocation


def _fetch_one(
    position: Portfolio,
    client: InvestAPIClient,
) -> tuple[Portfolio, Decimal | None, str, str]:
    quote: PriceQuote | None = None
    history: PriceHistory | None = None
    try:
        quote = get_quote(
            position.asset_type,
            position.asset_name,
            position.app_id,
            client=client,
        )
    except Exception:
        pass

    price = quote.price if quote else get_price(
        position.asset_type,
        position.asset_name,
        position.app_id,
        client=client,
    )

    sparkline = ""
    if price is not None:
        try:
            history = get_history(
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

    subtitle = asset_subtitle(
        quote,
        history,
        symbol=_display_ticker(position),
        asset_type=position.asset_type,
        app_id=position.app_id,
    )
    return position, price, sparkline, subtitle


def _fetch_market_data(
    positions: list[Portfolio],
) -> list[tuple[Portfolio, Decimal | None, str, str]]:
    with InvestAPIClient() as client:
        with ThreadPoolExecutor(max_workers=4) as executor:
            return list(executor.map(lambda p: _fetch_one(p, client), positions))


def _build_item_row(
    position: Portfolio,
    price: Decimal | None,
    sparkline: str,
    display_name: str = "",
) -> dict[str, Any]:
    icon_bg, icon_fg = _icon_colors(position.asset_type)
    ticker = _display_ticker(position)
    icon_text = _icon_text(position, ticker)
    subtitle = display_name

    if price is None:
        return {
            "ticker": ticker,
            "icon_text": icon_text,
            "name": subtitle,
            "detail_url": _detail_url(position),
            "meta": _meta_label(position),
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
        "icon_text": icon_text,
        "name": subtitle,
        "detail_url": _detail_url(position),
        "meta": _meta_label(position),
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
        "portfolio_value_short": "0",
        "position_count": 0,
        "unrealised_pnl": "0",
        "pnl_pos": True,
        "pnl_pct": "0",
        "allocation": [],
    }


def build_holdings(
    user,
    asset_type: str,
    *,
    app_id: int | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    positions_qs = Portfolio.objects.filter(user=user, asset_type=asset_type)
    if asset_type == AssetType.STEAM and app_id is not None:
        positions_qs = positions_qs.filter(app_id=app_id)
    positions = list(positions_qs.order_by("asset_name"))
    if not positions:
        return [], _empty_summary()

    market_rows = _fetch_market_data(positions)

    items: list[dict[str, Any]] = []
    total_value = Decimal("0")
    total_pnl = Decimal("0")
    cost_basis = Decimal("0")

    for position, price, sparkline, display_name in market_rows:
        row = _build_item_row(position, price, sparkline, display_name)
        items.append(row)
        if "_total_raw" in row:
            total_value += row["_total_raw"]
            total_pnl += row["_pnl_raw"]
            cost_basis += position.cost_basis()
        else:
            cost_basis += position.cost_basis()

    allocation = _build_value_allocation(items, total_value)

    for row in items:
        row.pop("_total_raw", None)
        row.pop("_pnl_raw", None)

    pnl_pct = Decimal("0")
    if cost_basis > 0:
        pnl_pct = (total_pnl / cost_basis) * 100

    dollars, _cents = f"{total_value:,.2f}".split(".")

    return items, {
        "portfolio_value": dollars,
        "portfolio_value_short": _format_value_short(total_value),
        "position_count": len(positions),
        "unrealised_pnl": _format_money(abs(total_pnl)),
        "pnl_pos": total_pnl >= 0,
        "pnl_pct": f"{pnl_pct:.1f}",
        "allocation": allocation,
    }
