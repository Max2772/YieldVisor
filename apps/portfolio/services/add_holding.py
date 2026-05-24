from __future__ import annotations

from decimal import Decimal

from django.db import transaction

from apps.history.models import History, HistoryOperation
from apps.portfolio.models import Portfolio


def _find_position(
    user,
    *,
    asset_type: str,
    asset_name: str,
    app_id: int | None,
) -> Portfolio | None:
    qs = Portfolio.objects.filter(
        user=user,
        asset_type=asset_type,
        asset_name=asset_name,
    )
    if app_id is not None:
        return qs.filter(app_id=app_id).first()
    return qs.filter(app_id__isnull=True).first()


@transaction.atomic
def add_holding(
    user,
    *,
    asset_type: str,
    asset_name: str,
    app_id: int | None,
    quantity: Decimal,
    buy_price: Decimal,
) -> Portfolio:
    position = _find_position(
        user,
        asset_type=asset_type,
        asset_name=asset_name,
        app_id=app_id,
    )

    if position is None:
        position = Portfolio.objects.create(
            user=user,
            asset_type=asset_type,
            asset_name=asset_name,
            app_id=app_id,
            quantity=quantity,
            avg_buy_price=buy_price,
        )
    else:
        old_qty = position.quantity
        new_qty = old_qty + quantity
        if new_qty > 0:
            position.avg_buy_price = (
                (old_qty * position.avg_buy_price) + (quantity * buy_price)
            ) / new_qty
        position.quantity = new_qty
        position.save(update_fields=["quantity", "avg_buy_price", "updated_at"])

    History.objects.create(
        user=user,
        portfolio=position,
        operation=HistoryOperation.BUY,
        asset_type=asset_type,
        asset_name=asset_name,
        app_id=app_id,
        quantity=quantity,
        price=buy_price,
    )
    return position
