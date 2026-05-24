from __future__ import annotations

from decimal import Decimal

from django import forms


class AddHoldingForm(forms.Form):
    quantity = forms.DecimalField(
        min_value=Decimal("0.00000001"),
        max_digits=38,
        decimal_places=8,
        label="Quantity",
    )
    buy_price = forms.DecimalField(
        min_value=Decimal("0.01"),
        max_digits=38,
        decimal_places=2,
        label="Buy price (USD)",
    )
