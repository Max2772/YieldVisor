from __future__ import annotations

from decimal import Decimal

from django import forms

from apps.portfolio.types import AssetType


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


class DeleteHoldingForm(forms.Form):
    position_id = forms.IntegerField(widget=forms.HiddenInput)
    next = forms.CharField(required=False, widget=forms.HiddenInput)
