from __future__ import annotations

from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError

from apps.alerts.models import AlertDirection
from apps.core.services.invest_api import InvestAPIError, get_quote
from apps.portfolio.types import AssetType

STEAM_DEFAULT_APP_ID = 730
ASSET_NOT_FOUND_MSG = "Asset not found. Check the name, type, and App ID."
ASSET_VERIFY_FAILED_MSG = "Could not verify asset. Try again later."


class CreateAlertForm(forms.Form):
    asset_type = forms.ChoiceField(choices=AssetType.choices)
    asset_name = forms.CharField(max_length=255)
    app_id = forms.IntegerField(required=False, min_value=1)
    direction = forms.ChoiceField(choices=AlertDirection.choices)
    target_price = forms.DecimalField(
        min_value=Decimal("0.01"),
        max_digits=38,
        decimal_places=8,
    )
    next = forms.CharField(required=False, widget=forms.HiddenInput)

    def clean_asset_name(self) -> str:
        return self.cleaned_data["asset_name"].strip()

    def clean(self) -> None:
        super().clean()
        if self._errors:
            return
        if self.cleaned_data.get("asset_type") == AssetType.STEAM:
            app_id = self.cleaned_data.get("app_id")
            self.cleaned_data["app_id"] = app_id if app_id is not None else STEAM_DEFAULT_APP_ID
        else:
            self.cleaned_data["app_id"] = None
        if self.cleaned_data.get("asset_type") == AssetType.CRYPTO:
            self.cleaned_data["asset_name"] = self.cleaned_data["asset_name"].lower()

        asset_type = self.cleaned_data["asset_type"]
        asset_name = self.cleaned_data["asset_name"]
        app_id = self.cleaned_data["app_id"]

        try:
            quote = get_quote(asset_type, asset_name, app_id)
        except InvestAPIError as exc:
            raise ValidationError({"asset_name": ASSET_VERIFY_FAILED_MSG}) from exc

        if quote is None:
            raise ValidationError({"asset_name": ASSET_NOT_FOUND_MSG})


class DeleteAlertForm(forms.Form):
    next = forms.CharField(required=False, widget=forms.HiddenInput)
