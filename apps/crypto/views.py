from __future__ import annotations

from typing import Any

from django.views.generic import TemplateView

from apps.core.mixins import AssetDetailMixin, AssetMarketMixin
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

    def get_hero_meta(self, **kwargs: Any) -> str:
        return "Cryptocurrency"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        return context
