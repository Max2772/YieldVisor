from __future__ import annotations

from typing import Any

from django.contrib import messages
from django.shortcuts import redirect
from django.views.generic import TemplateView

from apps.core.mixins import AssetDetailMixin, AssetMarketMixin
from apps.portfolio.forms import AddHoldingForm
from apps.portfolio.services.add_holding import add_holding
from apps.portfolio.types import AssetType


class CryptoView(AssetMarketMixin, TemplateView):
    template_name = 'crypto/crypto.html'
    asset_type = AssetType.CRYPTO
    active_nav = 'crypto'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Crypto'
        return context


class CryptoCoinView(AssetDetailMixin, TemplateView):
    """Страница отдельной монеты — данные из InvestAPI."""

    template_name = 'crypto/coin.html'
    asset_type = AssetType.CRYPTO
    list_url_name = 'crypto:crypto'
    list_label = 'Crypto'
    active_nav = 'crypto'
    asset_type_label = 'Crypto'

    def get_asset_params(self, **kwargs: Any) -> dict[str, Any]:
        coin = kwargs['coin'].strip()
        return {
            'asset_name': coin,
            'display_symbol': coin.upper(),
        }

    def get(self, request, *args, **kwargs):
        detail = self._load_detail(**kwargs)
        if detail is None:
            if self._load_error == "api":
                return self._render_asset_not_found(
                    request, self._asset_params, api_unavailable=True
                )
            return self._render_asset_not_found(request, self._asset_params)

        requested = kwargs["coin"].strip()
        canonical = (detail["asset"].get("coin_name") or "").strip()
        if canonical and canonical.lower() != requested.lower():
            return redirect(
                "crypto:coin",
                coin=canonical,
            )

        return self.render_to_response(self.get_context_data(**kwargs))

    def post(self, request, *args, **kwargs):
        detail = self._load_detail(**kwargs)
        if detail is None:
            if self._load_error == "api":
                return self._render_asset_not_found(
                    request, self._asset_params, api_unavailable=True
                )
            return self._render_asset_not_found(request, self._asset_params)

        form = AddHoldingForm(request.POST)
        if form.is_valid():
            canonical = (detail["asset"].get("coin_name") or "").strip()
            add_holding(
                request.user,
                asset_type=self.asset_type,
                asset_name=canonical or self._asset_params["asset_name"],
                app_id=self._asset_params.get("app_id"),
                quantity=form.cleaned_data["quantity"],
                buy_price=form.cleaned_data["buy_price"],
            )
            messages.success(
                request,
                f"Added {self._asset_params['display_symbol']} to portfolio.",
            )

            canonical = (self._asset_detail["asset"].get("coin_name") or "").strip()
            if canonical:
                return redirect("crypto:coin", coin=canonical)
            return redirect(request.path)

        context = self.get_context_data(**kwargs)
        context["add_form"] = form
        return self.render_to_response(context)
