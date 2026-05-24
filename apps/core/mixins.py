from __future__ import annotations

from typing import Any

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic import TemplateView

from apps.core.services.asset_detail import build_asset_detail_context
from apps.core.services.invest_api import InvestAPIError


class AssetDetailMixin(LoginRequiredMixin, TemplateView):
    """Загрузка карточки актива из InvestAPI; своя 404, если актив не найден."""

    asset_type: str = ""
    list_url_name: str = ""
    list_label: str = ""
    active_nav: str = ""
    asset_type_label: str = ""

    def get_asset_params(self, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

    def get_hero_meta(self, **kwargs: Any) -> str:
        return ""

    def _render_asset_not_found(
        self,
        request,
        params: dict[str, Any],
        *,
        api_unavailable: bool = False,
    ) -> HttpResponse:
        return render(
            request,
            "404.html",
            {
                "title": "Not Found",
                "symbol": params["display_symbol"],
                "category": self.asset_type_label,
                "list_url_name": self.list_url_name,
                "list_label": self.list_label,
                "active_nav": self.active_nav,
                "api_unavailable": api_unavailable,
            },
            status=404,
        )

    def get(self, request, *args, **kwargs):
        params = self.get_asset_params(**kwargs)
        try:
            detail = build_asset_detail_context(
                self.asset_type,
                params["asset_name"],
                display_symbol=params["display_symbol"],
                app_id=params.get("app_id"),
                asset_type_label=self.asset_type_label,
                hero_meta=self.get_hero_meta(**kwargs),
            )
        except InvestAPIError:
            return self._render_asset_not_found(request, params, api_unavailable=True)

        if detail is None:
            return self._render_asset_not_found(request, params)

        self._asset_detail = detail
        self._asset_params = params
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(self._asset_detail)
        context["title"] = self._asset_params["display_symbol"]
        context["active_nav"] = self.active_nav
        context["list_label"] = self.list_label
        context["list_url_name"] = self.list_url_name
        return context
