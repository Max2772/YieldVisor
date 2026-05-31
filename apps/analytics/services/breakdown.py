from __future__ import annotations

from decimal import Decimal
from typing import Any

from apps.portfolio.models import Portfolio
from apps.portfolio.services.holdings import _build_item_row, _format_money


def build_asset_breakdown(
    positions: list[Portfolio],
    market_rows: list[tuple[Any, ...]],
    total_value: Decimal,
) -> list[dict[str, Any]]:
    breakdown: list[dict[str, Any]] = []

    for position, price, sparkline, full_name, crypto_symbol in market_rows:
        row = _build_item_row(position, price, sparkline, full_name, crypto_symbol)
        if price is None:
            continue

        value = position.current_value(price)
        weight = int((value / total_value) * 100) if total_value > 0 else 0

        breakdown.append({
            "ticker": row["ticker"],
            "asset_type": position.asset_type,
            "type": position.asset_type.upper(),
            "logo_url": row.get("logo_url", ""),
            "icon_text": row["icon_text"],
            "icon_bg": row["icon_bg"],
            "icon_fg": row["icon_fg"],
            "detail_url": row["detail_url"],
            "cost": _format_money(position.cost_basis()),
            "value": row["total"],
            "pnl": row["pnl"],
            "pnl_pos": row["pnl_pos"],
            "ret_pct": row["pnl_pct"],
            "weight": max(weight, 1) if value > 0 else 0,
            "_sort": position.pnl_pct(price),
        })

    breakdown.sort(key=lambda item: item["_sort"], reverse=True)
    for item in breakdown:
        item.pop("_sort", None)

    remainder = 100 - sum(item["weight"] for item in breakdown)
    if remainder and breakdown:
        breakdown[0]["weight"] += remainder

    return breakdown
