from __future__ import annotations

from decimal import Decimal

from django.db import transaction

from apps.history.models import History, HistoryOperation
from apps.portfolio.models import Portfolio


def _detach_history(position: Portfolio) -> None:
    History.objects.filter(portfolio=position).update(portfolio=None)


@transaction.atomic
def sell_holding(
    user,
    *,
    position_id: int,
    quantity: Decimal,
    sell_price: Decimal,
) -> None:
    position = Portfolio.objects.select_for_update().get(pk=position_id, user=user)
    if quantity <= 0:
        raise ValueError("Quantity must be positive.")
    if quantity > position.quantity:
        raise ValueError("Quantity exceeds your holdings.")

    History.objects.create(
        user=user,
        portfolio=position,
        operation=HistoryOperation.SELL,
        asset_type=position.asset_type,
        asset_name=position.asset_name,
        app_id=position.app_id,
        quantity=quantity,
        price=sell_price,
    )

    new_qty = position.quantity - quantity
    if new_qty <= 0:
        _detach_history(position)
        position.delete()
    else:
        position.quantity = new_qty
        position.save(update_fields=["quantity", "updated_at"])


@transaction.atomic
def delete_holding(user, *, position_id: int) -> None:
    position = Portfolio.objects.select_for_update().get(pk=position_id, user=user)
    _detach_history(position)
    position.delete()
