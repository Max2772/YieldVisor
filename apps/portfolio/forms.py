from __future__ import annotations

from decimal import Decimal

from django import forms

from apps.portfolio.models import Portfolio
from apps.portfolio.types import AssetType

STEAM_WHOLE_QTY_ERROR = "Steam items can only be traded in whole units."


def _require_whole_quantity(quantity: Decimal) -> None:
    if quantity != quantity.to_integral_value():
        raise forms.ValidationError(STEAM_WHOLE_QTY_ERROR)


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

    def __init__(self, *args, asset_type: str | None = None, **kwargs):
        self.asset_type = asset_type
        super().__init__(*args, **kwargs)

    def clean_quantity(self):
        quantity = self.cleaned_data["quantity"]
        if self.asset_type == AssetType.STEAM:
            _require_whole_quantity(quantity)
        return quantity


class BuyHoldingForm(forms.Form):
    asset_type = forms.ChoiceField(choices=AssetType.choices)
    asset_name = forms.CharField(max_length=255)
    app_id = forms.IntegerField(required=False, min_value=1)
    quantity = forms.DecimalField(
        min_value=Decimal("0.00000001"),
        max_digits=38,
        decimal_places=8,
    )
    buy_price = forms.DecimalField(
        min_value=Decimal("0.01"),
        max_digits=38,
        decimal_places=2,
        label="Buy price (USD)",
    )
    next = forms.CharField(required=False, widget=forms.HiddenInput)

    def clean(self) -> None:
        super().clean()
        if self._errors:
            return
        if self.cleaned_data.get("asset_type") == AssetType.STEAM and not self.cleaned_data.get(
            "app_id",
        ):
            self.add_error("app_id", "App ID is required for Steam items.")
        elif self.cleaned_data.get("asset_type") != AssetType.STEAM:
            self.cleaned_data["app_id"] = None
        if self.cleaned_data.get("asset_type") == AssetType.STEAM:
            try:
                _require_whole_quantity(self.cleaned_data["quantity"])
            except forms.ValidationError as exc:
                self.add_error("quantity", exc)


class SellHoldingForm(forms.Form):
    position_id = forms.IntegerField(widget=forms.HiddenInput)
    next = forms.CharField(required=False, widget=forms.HiddenInput)
    quantity = forms.DecimalField(
        min_value=Decimal("0.00000001"),
        max_digits=38,
        decimal_places=8,
    )
    sell_price = forms.DecimalField(
        min_value=Decimal("0.01"),
        max_digits=38,
        decimal_places=2,
        label="Sell price (USD)",
    )

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        if self._errors or not self.user:
            return cleaned
        position_id = cleaned.get("position_id")
        quantity = cleaned.get("quantity")
        if position_id is None or quantity is None:
            return cleaned
        position = Portfolio.objects.filter(pk=position_id, user=self.user).first()
        if position and position.asset_type == AssetType.STEAM:
            try:
                _require_whole_quantity(quantity)
            except forms.ValidationError as exc:
                self.add_error("quantity", exc)
        return cleaned


class DeleteHoldingForm(forms.Form):
    position_id = forms.IntegerField(widget=forms.HiddenInput)
    next = forms.CharField(required=False, widget=forms.HiddenInput)
