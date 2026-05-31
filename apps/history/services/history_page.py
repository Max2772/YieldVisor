from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from datetime import timedelta
from decimal import Decimal
from typing import Any
from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Sum
from django.db.models.functions import Coalesce, TruncMonth
from django.urls import reverse
from django.utils import timezone

from apps.history.models import History, HistoryOperation
from apps.portfolio.services.holdings import _format_money, _format_qty
from apps.portfolio.services.market_page import _split_money_display
from apps.portfolio.types import AssetType

PAGE_SIZE = 25

SORT_FIELDS = {
    "-created_at": "-created_at",
    "created_at": "created_at",
    "-total": "-line_total",
    "total": "line_total",
}

TYPE_LABELS: dict[str, tuple[str, str]] = {
    AssetType.STOCK: ("Stocks", "#4fc3f7"),
    AssetType.CRYPTO: ("Crypto", "#7c83ff"),
    AssetType.STEAM: ("Steam", "#ffb300"),
}

MONTH_LABELS = (
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
)

_LINE_TOTAL = ExpressionWrapper(
    F("quantity") * F("price"),
    output_field=DecimalField(max_digits=38, decimal_places=2),
)


def _asset_key(tx: History) -> tuple[str, str, int | None]:
    return (tx.asset_type, tx.asset_name, tx.app_id)


def _fifo_realised_pnl(transactions: Iterable[History]) -> Decimal:
    lots: dict[tuple[str, str, int | None], list[list[Decimal]]] = defaultdict(list)
    pnl = Decimal("0")

    for tx in sorted(transactions, key=lambda row: row.created_at):
        key = _asset_key(tx)
        if tx.operation == HistoryOperation.BUY:
            lots[key].append([tx.quantity, tx.price])
            continue

        remaining = tx.quantity
        cost = Decimal("0")
        while remaining > 0 and lots[key]:
            lot_qty, lot_price = lots[key][0]
            take = min(remaining, lot_qty)
            cost += take * lot_price
            remaining -= take
            lot_qty -= take
            if lot_qty <= 0:
                lots[key].pop(0)
            else:
                lots[key][0] = [lot_qty, lot_price]
        pnl += tx.quantity * tx.price - cost
    return pnl


def _money_parts(value: Decimal) -> dict[str, Any]:
    dollars, cents = _split_money_display(abs(value))
    return {
        "dollars": dollars,
        "cents": cents,
        "positive": value >= 0,
        "sign": "+" if value >= 0 else "−",
    }


def _apply_filters(qs, params) -> Any:
    search = (params.get("search") or "").strip()
    if search:
        qs = qs.filter(asset_name__icontains=search)

    asset_type = (params.get("type") or "").strip()
    if asset_type in AssetType.values:
        qs = qs.filter(asset_type=asset_type)

    operation = (params.get("op") or "").strip()
    if operation in (HistoryOperation.BUY, HistoryOperation.SELL):
        qs = qs.filter(operation=operation)

    date_from = (params.get("date_from") or "").strip()
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)

    date_to = (params.get("date_to") or "").strip()
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)

    sort = (params.get("sort") or "-created_at").strip()
    order = SORT_FIELDS.get(sort, "-created_at")
    return qs.order_by(order)


def _asset_detail_url(tx: History) -> str:
    if tx.asset_type == AssetType.STOCK:
        return reverse("stocks:stock", kwargs={"ticker": tx.asset_name.upper()})
    if tx.asset_type == AssetType.CRYPTO:
        return reverse("crypto:coin", kwargs={"coin": tx.asset_name})
    if tx.asset_type == AssetType.STEAM and tx.app_id:
        return reverse(
            "steam:item",
            kwargs={"app_id": tx.app_id, "market_hash_name": tx.asset_name},
        )
    return ""


def _format_tx_datetime(dt) -> str:
    local = timezone.localtime(dt)
    return local.strftime("%d %b %H:%M")


def _build_tx_row(tx: History) -> dict[str, Any]:
    total = tx.quantity * tx.price
    return {
        "operation": tx.operation,
        "date_display": _format_tx_datetime(tx.created_at),
        "asset_name": tx.asset_name,
        "asset_type": tx.asset_type,
        "asset_type_label": tx.get_asset_type_display().upper(),
        "detail_url": _asset_detail_url(tx),
        "quantity": _format_qty(tx.quantity),
        "price": _format_money(tx.price),
        "total": _format_money(total),
    }


def _build_export_row(tx: History) -> dict[str, str]:
    total = tx.quantity * tx.price
    return {
        "date": timezone.localtime(tx.created_at).strftime("%Y-%m-%d %H:%M"),
        "operation": tx.operation.upper(),
        "asset": tx.asset_name,
        "type": tx.get_asset_type_display(),
        "qty": _format_qty(tx.quantity),
        "price": f"{tx.price:.2f}",
        "total": f"{total:.2f}",
    }


def _monthly_volume(user) -> dict[str, Any]:
    today = timezone.localdate()
    start = today.replace(day=1) - timedelta(days=150)
    start = start.replace(day=1)

    rows = (
        History.objects.filter(user=user, created_at__date__gte=start)
        .annotate(month=TruncMonth("created_at"))
        .values("month", "operation")
        .annotate(volume=Coalesce(Sum(_LINE_TOTAL), Decimal("0")))
        .order_by("month")
    )

    month_keys: list[tuple[int, int]] = []
    cursor = start
    while cursor <= today:
        month_keys.append((cursor.year, cursor.month))
        if cursor.month == 12:
            cursor = cursor.replace(year=cursor.year + 1, month=1)
        else:
            cursor = cursor.replace(month=cursor.month + 1)

    buy_by_month: dict[tuple[int, int], Decimal] = defaultdict(lambda: Decimal("0"))
    sell_by_month: dict[tuple[int, int], Decimal] = defaultdict(lambda: Decimal("0"))
    for row in rows:
        month = row["month"]
        if month is None:
            continue
        key = (month.year, month.month)
        if row["operation"] == HistoryOperation.BUY:
            buy_by_month[key] = row["volume"]
        else:
            sell_by_month[key] = row["volume"]

    labels: list[str] = []
    buys: list[float] = []
    sells: list[float] = []
    for key in month_keys[-6:]:
        labels.append(MONTH_LABELS[key[1] - 1])
        buys.append(float(buy_by_month[key]))
        sells.append(float(sell_by_month[key]))

    return {"labels": labels, "buys": buys, "sells": sells}


def _type_breakdown(user) -> dict[str, Any]:
    counts = {
        row["asset_type"]: row["count"]
        for row in History.objects.filter(user=user)
        .values("asset_type")
        .annotate(count=Count("id"))
    }
    total = sum(counts.values())
    segments: list[dict[str, Any]] = []
    legend: list[dict[str, Any]] = []

    for asset_type in (AssetType.STOCK, AssetType.CRYPTO, AssetType.STEAM):
        count = counts.get(asset_type, 0)
        label, color = TYPE_LABELS[asset_type]
        pct = int(round(count * 100 / total)) if total else 0
        segments.append({"value": count or 0, "color": color})
        legend.append({"label": label, "pct": pct, "color": color})

    if total and legend:
        remainder = 100 - sum(item["pct"] for item in legend)
        if remainder:
            largest = max(legend, key=lambda item: item["pct"])
            largest["pct"] += remainder

    return {
        "total_txns": total,
        "segments": segments,
        "legend": legend,
    }


def _this_month_stats(user) -> dict[str, Any]:
    today = timezone.localdate()
    month_start = today.replace(day=1)
    qs = History.objects.filter(user=user, created_at__date__gte=month_start).annotate(
        line_total=_LINE_TOTAL,
    )

    invested = qs.filter(operation=HistoryOperation.BUY).aggregate(
        total=Coalesce(Sum("line_total"), Decimal("0")),
    )["total"]
    sold = qs.filter(operation=HistoryOperation.SELL).aggregate(
        total=Coalesce(Sum("line_total"), Decimal("0")),
    )["total"]
    net = sold - invested

    most_traded = (
        qs.values("asset_name")
        .annotate(c=Count("id"))
        .order_by("-c", "asset_name")
        .first()
    )

    return {
        "month_txn_count": qs.count(),
        "month_invested": _format_money(invested),
        "month_sold": _format_money(sold),
        "month_net": _format_money(abs(net)),
        "month_net_sign": "+" if net >= 0 else "−",
        "month_net_pos": net >= 0,
        "most_traded": most_traded["asset_name"] if most_traded else "—",
    }


def build_history_page_context(user, *, params) -> dict[str, Any]:
    base_qs = (
        History.objects.filter(user=user)
        .select_related("portfolio")
        .annotate(line_total=_LINE_TOTAL)
    )
    all_txns = list(base_qs.order_by("created_at"))

    buy_qs = base_qs.filter(operation=HistoryOperation.BUY)
    sell_qs = base_qs.filter(operation=HistoryOperation.SELL)
    total_invested = buy_qs.aggregate(
        total=Coalesce(Sum("line_total"), Decimal("0")),
    )["total"]
    total_sold = sell_qs.aggregate(
        total=Coalesce(Sum("line_total"), Decimal("0")),
    )["total"]
    realised = _fifo_realised_pnl(all_txns)

    filtered_qs = _apply_filters(base_qs, params)
    paginator = Paginator(filtered_qs, PAGE_SIZE)
    page_number = params.get("page") or 1
    page_obj = paginator.get_page(page_number)

    if hasattr(params, "urlencode"):
        query_params = params.copy()
        query_params.pop("page", None)
        filter_query = query_params.urlencode()
    else:
        filter_query = urlencode(
            {key: value for key, value in params.items() if key != "page" and value},
        )

    invested_parts = _money_parts(total_invested)
    sold_parts = _money_parts(total_sold)
    realised_parts = _money_parts(realised)

    type_data = _type_breakdown(user)
    volume = _monthly_volume(user)

    return {
        "total_invested_dollars": invested_parts["dollars"],
        "total_invested_cents": invested_parts["cents"],
        "buy_count": buy_qs.count(),
        "total_sold_dollars": sold_parts["dollars"],
        "total_sold_cents": sold_parts["cents"],
        "sell_count": sell_qs.count(),
        "realised_pnl_dollars": realised_parts["dollars"],
        "realised_pnl_cents": realised_parts["cents"],
        "realised_pos": realised_parts["positive"],
        "realised_sign": realised_parts["sign"],
        "total_txns": len(all_txns),
        "history": [_build_tx_row(tx) for tx in page_obj.object_list],
        "history_export": [_build_export_row(tx) for tx in filtered_qs],
        "page_obj": page_obj,
        "filter_query": filter_query,
        **type_data,
        "volume_chart": volume,
        "type_chart_values": [segment["value"] for segment in type_data["segments"]],
        "type_chart_colors": [segment["color"] for segment in type_data["segments"]],
        **_this_month_stats(user),
    }
