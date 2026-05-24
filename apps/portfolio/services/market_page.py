from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from decimal import Decimal
from typing import Any

from django.urls import reverse
from django.utils import timezone
from django.utils.timesince import timesince

from apps.core.market_catalog import PORTFOLIO_CHART_DAYS, catalog_for_asset_type
from apps.core.services.asset_detail import _chart_label
from apps.core.services.invest_api import (
    InvestAPIClient,
    PriceHistoryPoint,
    get_history,
    get_quote,
    period_change_pct,
)
from apps.core.services.ticker import format_change_delta, format_ticker_price
from apps.portfolio.models import Portfolio
from apps.portfolio.services.holdings import build_holdings
from apps.portfolio.types import AssetType


def _format_money(value: Decimal) -> str:
    q = value.quantize(Decimal("0.01"))
    if q >= Decimal("1000"):
        return f"{q:,.2f}"
    return f"{q:.2f}"


def _split_money_display(value: Decimal) -> tuple[str, str]:
    formatted = f"{value:,.2f}"
    dollars, cents = formatted.split(".")
    return dollars, cents


def _parse_cached_at(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if timezone.is_naive(dt):
            return timezone.make_aware(dt, timezone.get_current_timezone())
        return dt
    except ValueError:
        return None


def _format_last_update(cached_times: list[datetime]) -> str:
    if not cached_times:
        return "—"
    latest = max(cached_times)
    if timezone.is_naive(latest):
        latest = timezone.make_aware(latest, timezone.get_current_timezone())
    return f"{timesince(latest)} ago"


def _detail_url_for(
    asset_type: str,
    asset_name: str,
    app_id: int | None,
) -> str:
    if asset_type == AssetType.STOCK:
        return reverse("stocks:stock", kwargs={"ticker": asset_name.upper()})
    if asset_type == AssetType.CRYPTO:
        return reverse("crypto:coin", kwargs={"coin": asset_name})
    if asset_type == AssetType.STEAM and app_id:
        return reverse(
            "steam:item",
            kwargs={"app_id": app_id, "market_hash_name": asset_name},
        )
    return "#"


def _fetch_market_result(
    asset_type: str,
    asset_name: str,
    *,
    app_id: int | None,
    symbol: str,
    client: InvestAPIClient,
) -> dict[str, Any] | None:
    try:
        history = get_history(
            asset_type,
            asset_name,
            app_id,
            days=7,
            client=client,
        )
    except Exception:
        history = None

    quote = None
    try:
        quote = get_quote(asset_type, asset_name, app_id, client=client)
    except Exception:
        pass

    if quote is None and (history is None or not history.points):
        return None

    price = quote.price if quote else history.points[-1].price
    change_pct: Decimal | None = None
    if history and history.points:
        change_pct = period_change_pct(history.points)

    change = "—"
    pos = True
    if change_pct is not None:
        change, pos = format_change_delta(change_pct)

    display_name = ""
    if quote and quote.full_name:
        display_name = quote.full_name
    elif quote:
        display_name = quote.name
    elif history and history.full_name:
        display_name = history.full_name
    elif history:
        display_name = history.name

    subtitle = display_name if display_name and display_name != symbol else ""
    if asset_type == AssetType.STEAM and app_id:
        subtitle = subtitle or f"App {app_id}"

    return {
        "symbol": symbol,
        "name": subtitle,
        "price": format_ticker_price(price).lstrip("$"),
        "change": change,
        "pos": pos,
        "detail_url": _detail_url_for(asset_type, asset_name, app_id),
    }


def build_market_search_results(asset_type: str) -> list[dict[str, Any]]:
    catalog = catalog_for_asset_type(asset_type)
    if not catalog:
        return []

    with InvestAPIClient() as client:
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for entry in catalog:
                if asset_type == AssetType.STOCK:
                    futures.append(
                        executor.submit(
                            _fetch_market_result,
                            asset_type,
                            entry["asset_name"],
                            app_id=None,
                            symbol=entry["asset_name"].upper(),
                            client=client,
                        )
                    )
                elif asset_type == AssetType.CRYPTO:
                    futures.append(
                        executor.submit(
                            _fetch_market_result,
                            asset_type,
                            entry["asset_name"],
                            app_id=None,
                            symbol=entry["symbol"],
                            client=client,
                        )
                    )
                else:
                    futures.append(
                        executor.submit(
                            _fetch_market_result,
                            asset_type,
                            entry["asset_name"],
                            app_id=entry["app_id"],
                            symbol=entry["asset_name"][:24],
                            client=client,
                        )
                    )

            return [row for future in futures if (row := future.result())]


def _build_portfolio_chart(
    positions: list[Portfolio],
    client: InvestAPIClient,
    *,
    days: int = PORTFOLIO_CHART_DAYS,
) -> dict[str, list[Any]]:
    if not positions:
        return {"labels": [], "values": []}

    series: list[tuple[Decimal, list[PriceHistoryPoint]]] = []
    for position in positions:
        try:
            history = get_history(
                position.asset_type,
                position.asset_name,
                position.app_id,
                days=days,
                client=client,
            )
        except Exception:
            history = None
        if history and history.points:
            series.append((position.quantity, list(history.points)))

    if not series:
        return {"labels": [], "values": []}

    min_len = min(len(points) for _, points in series)
    labels = [_chart_label(series[0][1][-min_len + i].timestamp) for i in range(min_len)]
    values: list[float] = []
    for i in range(min_len):
        idx = -min_len + i
        total = sum(float(qty * points[idx].price) for qty, points in series)
        values.append(round(total, 2))

    return {"labels": labels, "values": values}


def _compute_performers(
    positions: list[Portfolio],
    items: list[dict[str, Any]],
) -> tuple[dict[str, str] | None, dict[str, str] | None]:
    by_ticker = {row["ticker"]: row for row in items}
    ranked: list[tuple[Decimal, dict[str, Any]]] = []

    for position in positions:
        ticker = (
            position.asset_name[:20]
            if position.asset_type == AssetType.STEAM
            else position.asset_name.upper()
        )
        row = by_ticker.get(ticker)
        if not row or row["market_price"] == "—":
            continue
        cost = position.cost_basis()
        if cost <= 0:
            continue
        try:
            market = Decimal(row["total"].replace(",", ""))
        except Exception:
            continue
        pnl_pct = ((market - cost) / cost) * Decimal("100")
        ranked.append((pnl_pct, row))

    if not ranked:
        return None, None

    best_pct, best_row = max(ranked, key=lambda pair: pair[0])
    worst_pct, worst_row = min(ranked, key=lambda pair: pair[0])

    def pack(row: dict[str, Any], pct: Decimal) -> dict[str, str]:
        sign = "+" if pct >= 0 else "−"
        return {"label": row["ticker"], "change": f"{sign}{abs(pct):.1f}%"}

    return pack(best_row, best_pct), pack(worst_row, worst_pct)


def _sum_cost_basis(positions: list[Portfolio]) -> Decimal:
    return sum((position.cost_basis() for position in positions), Decimal("0"))


def _best_item_total(
    best: dict[str, str] | None,
    items: list[dict[str, Any]],
) -> str:
    if not best:
        return "—"
    for row in items:
        if row["ticker"] == best["label"]:
            return row["total"]
    return "—"


def build_market_page_context(user, asset_type: str) -> dict[str, Any]:
    items, summary = build_holdings(user, asset_type)
    positions = list(
        Portfolio.objects.filter(user=user, asset_type=asset_type).order_by("asset_name")
    )

    best, worst = _compute_performers(positions, items)

    cached_times: list[datetime] = []
    with InvestAPIClient() as client:
        portfolio_chart = _build_portfolio_chart(positions, client)
        for position in positions:
            quote = get_quote(
                position.asset_type,
                position.asset_name,
                position.app_id,
                client=client,
            )
            if quote and quote.cached_at:
                parsed = _parse_cached_at(quote.cached_at)
                if parsed:
                    cached_times.append(parsed)

    market_results = build_market_search_results(asset_type)

    try:
        total_value = Decimal(summary["portfolio_value"].replace(",", ""))
    except Exception:
        total_value = Decimal("0")

    dollars, cents = _split_money_display(total_value)
    cost_basis = _sum_cost_basis(positions)

    ctx: dict[str, Any] = {
        "items": items,
        **summary,
        "portfolio_value_dollars": dollars,
        "portfolio_value_cents": cents,
        "cost_basis": _format_money(cost_basis),
        "market_results": market_results,
        "portfolio_chart": portfolio_chart,
        "last_price_update": _format_last_update(cached_times),
        "coin_count": summary["position_count"],
        "item_count": summary["position_count"],
    }

    if asset_type == AssetType.STOCK:
        ctx["best_ticker"] = best["label"] if best else "—"
        ctx["best_change"] = best["change"] if best else "—"
        ctx["worst_ticker"] = worst["label"] if worst else "—"
    elif asset_type == AssetType.CRYPTO:
        ctx["best_coin"] = best["label"] if best else "—"
        ctx["best_change"] = best["change"] if best else "—"
        ctx["worst_coin"] = worst["label"] if worst else "—"
    else:
        ctx["best_item"] = best["label"] if best else "—"
        ctx["best_item_val"] = _best_item_total(best, items)
        ctx["worst_item"] = worst["label"] if worst else "—"
        ctx["inv_value"] = summary["portfolio_value"]
        ctx["inv_value_short"] = summary["portfolio_value_short"]
        ctx["steam_pnl"] = summary["unrealised_pnl"]
        ctx["steam_pnl_pos"] = summary["pnl_pos"]
        ctx["steam_pnl_pct"] = (
            f"{'+' if summary['pnl_pos'] else '−'}{summary['pnl_pct']}"
        )

    return ctx
