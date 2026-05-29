from __future__ import annotations

import bisect
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from django.urls import reverse
from django.utils import timezone
from django.utils.timesince import timesince

from apps.core.market_catalog import (
    PORTFOLIO_CHART_DAYS,
    PORTFOLIO_CHART_MAX_DAYS,
    PORTFOLIO_CHART_MAX_DAYS_CRYPTO,
    catalog_for_asset_type,
)
from apps.core.services.asset_detail import _chart_label
from apps.core.services.asset_display import asset_subtitle
from apps.core.services.asset_logos import asset_logo_url
from apps.core.services.invest_api import (
    InvestAPIClient,
    PriceHistoryPoint,
    PriceQuote,
    get_crypto_quotes,
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


def _collect_cached_times(
    positions: list[Portfolio],
    client: InvestAPIClient,
) -> list[datetime]:
    times: list[datetime] = []
    crypto_names = [
        position.asset_name
        for position in positions
        if position.asset_type == AssetType.CRYPTO
    ]
    crypto_quotes: dict[str, PriceQuote] = {}
    if crypto_names:
        try:
            crypto_quotes = get_crypto_quotes(crypto_names, client=client)
        except Exception:
            pass

    for position in positions:
        quote: PriceQuote | None = None
        if position.asset_type == AssetType.CRYPTO:
            quote = crypto_quotes.get(position.asset_name.strip().lower())
        else:
            try:
                quote = get_quote(
                    position.asset_type,
                    position.asset_name,
                    position.app_id,
                    client=client,
                )
            except Exception:
                pass
        if quote and quote.cached_at:
            parsed = _parse_cached_at(quote.cached_at)
            if parsed:
                times.append(parsed)
    return times


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

    if history is None or not history.points:
        return None

    price = history.points[-1].price
    change_pct = period_change_pct(history.points)

    change = "—"
    pos = True
    if change_pct is not None:
        change, pos = format_change_delta(change_pct)

    subtitle = asset_subtitle(
        None,
        history,
        symbol=symbol,
        asset_type=asset_type,
        app_id=app_id,
    )

    return {
        "symbol": symbol,
        "name": subtitle,
        "logo_url": asset_logo_url(
            asset_type,
            ticker=symbol,
            asset_name=asset_name,
            app_id=app_id,
            crypto_symbol=symbol if asset_type == AssetType.CRYPTO else None,
        ),
        "price": format_ticker_price(price).lstrip("$"),
        "change": change,
        "pos": pos,
        "detail_url": _detail_url_for(asset_type, asset_name, app_id),
    }


def build_market_search_results(
    asset_type: str,
    *,
    app_id: int | None = None,
) -> list[dict[str, Any]]:
    catalog = catalog_for_asset_type(asset_type)
    if not catalog:
        return []

    with InvestAPIClient() as client:
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for entry in catalog:
                if (
                    asset_type == AssetType.STEAM
                    and app_id is not None
                    and entry.get("app_id") != app_id
                ):
                    continue
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
                            symbol=entry["asset_name"],
                            client=client,
                        )
                    )

            return [row for future in futures if (row := future.result())]


def _history_day_key(timestamp: str) -> str:
    return timestamp[:10] if timestamp else ""


def _contrib_by_day_sorted(
    qty: Decimal,
    points: list[PriceHistoryPoint],
) -> list[tuple[str, float]]:
    """One (calendar day → position value) per day; last observation wins that day."""
    by_day: dict[str, float] = {}
    for p in points:
        d = _history_day_key(p.timestamp)
        if not d:
            continue
        by_day[d] = float(qty * p.price)
    return sorted(by_day.items(), key=lambda pair: pair[0])


def _value_on_or_before(
    sorted_day_values: list[tuple[str, float]],
    day: str,
) -> float | None:
    days = [pair[0] for pair in sorted_day_values]
    i = bisect.bisect_right(days, day) - 1
    if i < 0:
        return None
    return sorted_day_values[i][1]


def _merge_portfolio_history_by_day(
    series: list[tuple[Decimal, list[PriceHistoryPoint]]],
) -> list[tuple[str, float]]:
    """Align holdings by calendar date; forward-fill each line so totals are not index-misaligned."""
    per_asset = [_contrib_by_day_sorted(qty, pts) for qty, pts in series]
    event_days = sorted({d for pairs in per_asset for d, _ in pairs})
    merged: list[tuple[str, float]] = []
    for d in event_days:
        total = 0.0
        for pairs in per_asset:
            v = _value_on_or_before(pairs, d)
            if v is None:
                total = 0.0
                break
            total += v
        else:
            merged.append((d, round(total, 2)))
    return merged


def slice_portfolio_chart_calendar_days(
    chart: dict[str, Any],
    *,
    days: int,
    cap: int,
) -> dict[str, list[Any]]:
    """Subset of chart for the last `min(days, cap)` calendar days (e.g. stat badge)."""
    points = chart.get("points") or []
    if len(points) < 2:
        return {"labels": list(chart.get("labels") or []), "values": list(chart.get("values") or [])}

    span = min(days, cap)
    last_raw = (points[-1].get("t") or "")[:10]
    try:
        last_d = date.fromisoformat(last_raw)
    except ValueError:
        return {"labels": list(chart.get("labels") or []), "values": list(chart.get("values") or [])}

    cutoff = last_d - timedelta(days=span)
    filtered: list[dict[str, Any]] = []
    for p in points:
        d_raw = (p.get("t") or "")[:10]
        try:
            d = date.fromisoformat(d_raw)
        except ValueError:
            continue
        if d >= cutoff:
            filtered.append(p)

    if len(filtered) < 2:
        filtered = list(points)

    return {
        "labels": [_chart_label(str(p.get("t") or "")) for p in filtered],
        "values": [p["v"] for p in filtered],
    }


def _build_portfolio_chart(
    positions: list[Portfolio],
    client: InvestAPIClient,
    *,
    days: int = PORTFOLIO_CHART_DAYS,
    per_asset_max_range: bool = False,
) -> dict[str, list[Any]]:
    if not positions:
        return {"labels": [], "values": [], "points": []}

    series: list[tuple[Decimal, list[PriceHistoryPoint]]] = []
    for position in positions:
        req_days = (
            (
                PORTFOLIO_CHART_MAX_DAYS_CRYPTO
                if position.asset_type == AssetType.CRYPTO
                else PORTFOLIO_CHART_MAX_DAYS
            )
            if per_asset_max_range
            else days
        )
        try:
            history = get_history(
                position.asset_type,
                position.asset_name,
                position.app_id,
                days=req_days,
                client=client,
            )
        except Exception:
            history = None
        if history and history.points:
            series.append((position.quantity, list(history.points)))

    if not series:
        return {"labels": [], "values": [], "points": []}

    merged = _merge_portfolio_history_by_day(series)
    labels: list[str] = []
    values: list[float] = []
    chart_points: list[dict[str, Any]] = []
    for day, value in merged:
        ts = f"{day}T00:00:00"
        labels.append(_chart_label(ts))
        values.append(value)
        chart_points.append({"t": ts, "v": value})

    return {"labels": labels, "values": values, "points": chart_points}


def _compute_performers(
    positions: list[Portfolio],
    items: list[dict[str, Any]],
) -> tuple[dict[str, str] | None, dict[str, str] | None]:
    return _compute_performers_with_asset_type(positions, items, positions[0].asset_type if positions else "")


def _compute_performers_with_asset_type(
    positions: list[Portfolio],
    items: list[dict[str, Any]],
    asset_type: str,
) -> tuple[dict[str, str] | None, dict[str, str] | None]:
    by_ticker = {row["ticker"]: row for row in items}
    ranked: list[tuple[Decimal, dict[str, Any]]] = []

    for position in positions:
        ticker = (
            position.asset_name
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
        label = row["ticker"]
        if asset_type == AssetType.CRYPTO:
            label = row.get("full_name") or row["ticker"]
        return {"label": label, "change": f"{sign}{abs(pct):.1f}%"}

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


def build_market_page_context(
    user,
    asset_type: str,
    *,
    app_id: int | None = None,
) -> dict[str, Any]:
    steam_app_id = app_id if asset_type == AssetType.STEAM else None
    items, summary = build_holdings(user, asset_type, app_id=steam_app_id)
    positions_qs = Portfolio.objects.filter(user=user, asset_type=asset_type)
    if steam_app_id is not None:
        positions_qs = positions_qs.filter(app_id=steam_app_id)
    positions = list(positions_qs.order_by("asset_name"))

    best, worst = _compute_performers_with_asset_type(
        positions,
        items,
        asset_type,
    )

    chart_fetch_days = (
        PORTFOLIO_CHART_MAX_DAYS_CRYPTO
        if asset_type == AssetType.CRYPTO
        else PORTFOLIO_CHART_MAX_DAYS
    )

    cached_times: list[datetime] = []
    with InvestAPIClient() as client:
        portfolio_chart = _build_portfolio_chart(
            positions,
            client,
            days=chart_fetch_days,
        )
        cached_times.extend(
            _collect_cached_times(positions, client),
        )

    market_results = build_market_search_results(asset_type, app_id=steam_app_id)

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
        "chart_period_cap": chart_fetch_days,
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
        ctx["steam_pnl_pct"] = summary["pnl_pct"]

    return ctx
