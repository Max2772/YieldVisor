from __future__ import annotations

from typing import Any
from urllib.parse import unquote

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from apps.core.mixins import AssetDetailMixin
from apps.portfolio.types import AssetType

STEAM_APP_LABELS = {
    730: 'Counter-Strike 2',
    570: 'Dota 2',
    440: 'Team Fortress 2',
}


class SteamView(LoginRequiredMixin, TemplateView):
    template_name = 'steam/steam.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Steam'
        context['active_nav'] = 'steam'
        return context


class SteamItemView(AssetDetailMixin, TemplateView):
    """Страница предмета Steam Market — данные из InvestAPI."""

    template_name = 'steam/item.html'
    asset_type = AssetType.STEAM
    list_url_name = 'steam:steam'
    list_label = 'Steam'
    active_nav = 'steam'
    asset_type_label = 'Steam Item'

    def get_asset_params(self, **kwargs: Any) -> dict[str, Any]:
        market_hash_name = unquote(kwargs['market_hash_name']).strip()
        return {
            'asset_name': market_hash_name,
            'display_symbol': market_hash_name,
            'app_id': kwargs['app_id'],
        }

    def get_hero_meta(self, **kwargs: Any) -> str:
        app_id = kwargs['app_id']
        game = STEAM_APP_LABELS.get(app_id, f'App {app_id}')
        return f"{game} · App ID {app_id}"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context['asset_type_emoji'] = '🎮'
        return context
