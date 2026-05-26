from __future__ import annotations

from typing import Any

from django.views.generic import TemplateView

from apps.core.mixins import AssetDetailMixin, AssetMarketMixin
from apps.portfolio.types import AssetType


class StockMarket(AssetMarketMixin, TemplateView):
    template_name = 'stocks/stocks.html'
    asset_type = AssetType.STOCK
    active_nav = 'stocks'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Stocks'
        return context


class StockView(AssetDetailMixin, TemplateView):
    """Страница отдельной бумаги — данные из InvestAPI."""

    template_name = 'stocks/stock.html'
    asset_type = AssetType.STOCK
    list_url_name = 'stocks:market'
    list_label = 'Stocks'
    active_nav = 'stocks'
    asset_type_label = 'Stock'

    def get_asset_params(self, **kwargs: Any) -> dict[str, Any]:
        ticker = kwargs['ticker'].strip().upper()
        return {
            'asset_name': ticker,
            'display_symbol': ticker,
        }

    def get_hero_meta(self, **kwargs: Any) -> str:
        ticker = kwargs['ticker'].strip().upper()
        return ticker

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        return context
