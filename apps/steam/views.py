from __future__ import annotations

from typing import Any
from urllib.parse import unquote

from django.views.generic import TemplateView

from apps.core.mixins import AssetDetailMixin, AssetMarketMixin
from apps.portfolio.types import AssetType
from apps.steam.constants import (
    STEAM_APP_FULL_LABELS,
    STEAM_APPS,
    resolve_steam_app_filter,
)


class SteamView(AssetMarketMixin, TemplateView):
    template_name = 'steam/steam.html'
    asset_type = AssetType.STEAM
    active_nav = 'steam'

    def get_market_page_options(self) -> dict[str, Any]:
        return {"app_id": resolve_steam_app_filter(self.request.GET.get("app"))}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        app_filter = resolve_steam_app_filter(self.request.GET.get("app"))
        context["title"] = "Steam"
        context["steam_apps"] = STEAM_APPS
        context["selected_app_filter"] = app_filter
        return context


class SteamItemView(AssetDetailMixin, TemplateView):
    """Страница предмета Steam Market — данные из InvestAPI."""

    template_name = 'steam/item.html'
    asset_type = AssetType.STEAM
    list_url_name = 'steam:steam'
    list_label = 'Steam'
    active_nav = 'steam'
    asset_type_label = 'Steam'

    def get_asset_params(self, **kwargs: Any) -> dict[str, Any]:
        market_hash_name = unquote(kwargs['market_hash_name']).strip()
        return {
            'asset_name': market_hash_name,
            'display_symbol': market_hash_name,
            'app_id': kwargs['app_id'],
        }

    def get_hero_meta(self, **kwargs: Any) -> str:
        app_id = kwargs['app_id']
        game = STEAM_APP_FULL_LABELS.get(app_id, f'App {app_id}')
        return f"{game} · App ID {app_id}"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        return context
