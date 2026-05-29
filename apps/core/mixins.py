from __future__ import annotations

from typing import Any

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic import TemplateView

from apps.core.services.asset_detail import build_asset_detail_context
from apps.core.services.invest_api import InvestAPIError
from apps.portfolio.models import Portfolio
from apps.portfolio.services.holdings import (
    _format_money,
    build_holding_trade_context,
    format_position_display,
)
from apps.portfolio.services.market_page import build_market_page_context
from apps.portfolio.types import AssetType


class AssetMarketMixin(LoginRequiredMixin, TemplateView):
    """Список активов пользователя по категории с ценами из API."""

    asset_type: str = ""
    active_nav: str = ""

    def get_market_page_options(self) -> dict[str, Any]:
        return {}

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(
            build_market_page_context(
                self.request.user,
                self.asset_type,
                **self.get_market_page_options(),
            )
        )
        context["active_nav"] = self.active_nav
        return context


class AssetDetailMixin(LoginRequiredMixin, TemplateView):
    """Карточка актива из InvestAPI; добавление в портфель; 404 если не найден."""

    asset_type: str = ""
    list_url_name: str = ""
    list_label: str = ""
    active_nav: str = ""
    asset_type_label: str = ""

    def get_asset_params(self, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

    def get_hero_meta(self, **kwargs: Any) -> str:
        return ""

    def _get_portfolio_position(self, params: dict[str, Any]) -> Portfolio | None:
        qs = Portfolio.objects.filter(
            user=self.request.user,
            asset_type=self.asset_type,
            asset_name=params["asset_name"],
        )
        app_id = params.get("app_id")
        if app_id is not None:
            return qs.filter(app_id=app_id).first()
        return qs.filter(app_id__isnull=True).first()

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

    def _load_detail(self, **kwargs: Any) -> dict[str, Any] | None:
        params = self.get_asset_params(**kwargs)
        self._asset_params = params
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
            self._load_error = "api"
            return None
        if detail is None:
            self._load_error = "not_found"
            return None
        self._load_error = None
        self._asset_detail = detail
        return detail

    def get(self, request, *args, **kwargs):
        if self._load_detail(**kwargs) is None:
            if self._load_error == "api":
                return self._render_asset_not_found(
                    request, self._asset_params, api_unavailable=True
                )
            return self._render_asset_not_found(request, self._asset_params)

        return super().get(request, *args, **kwargs)

    def _apply_holding_metrics(
        self,
        asset: dict[str, Any],
        position: Portfolio | None,
    ) -> None:
        price_raw = asset.get("price_raw")
        if position is None or price_raw is None:
            asset["has_holding"] = False
            return

        pnl_value = position.pnl(price_raw)
        pnl_pct = position.pnl_pct(price_raw)
        asset["has_holding"] = True
        asset["holding_pnl"] = _format_money(abs(pnl_value))
        asset["holding_pnl_positive"] = pnl_value >= 0
        asset["holding_pnl_pct"] = f"{pnl_pct:.1f}"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(self._asset_detail)
        context["title"] = self._asset_params["display_symbol"]
        context["active_nav"] = self.active_nav
        context["list_label"] = self.list_label
        context["list_url_name"] = self.list_url_name
        position = self._get_portfolio_position(self._asset_params)
        context["portfolio_position"] = position
        self._apply_holding_metrics(
            context["asset"],
            position,
        )
        trade_name = self._asset_params["asset_name"]
        if self.asset_type == AssetType.CRYPTO:
            coin = (context["asset"].get("coin_name") or "").strip()
            if coin:
                trade_name = coin
        context["holding_trade"] = build_holding_trade_context(
            asset_type=self.asset_type,
            asset_name=trade_name,
            display_ticker=self._asset_params["display_symbol"],
            app_id=self._asset_params.get("app_id"),
            current_price=context["asset"].get("price_raw"),
            position=position,
        )
        context["detail_asset_type"] = self.asset_type
        context["position_display"] = (
            format_position_display(position) if position else None
        )
        return context
