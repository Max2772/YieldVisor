from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods
from django.views.generic import TemplateView, View

from apps.portfolio.forms import BuyHoldingForm, DeleteHoldingForm, SellHoldingForm
from apps.portfolio.models import Portfolio
from apps.portfolio.services.add_holding import add_holding
from apps.portfolio.services.holding_actions import delete_holding, sell_holding
from apps.portfolio.services.portfolio_overview import build_portfolio_overview_context


def _wants_json(request) -> bool:
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def _form_errors_payload(form) -> dict[str, list[str]]:
    return {field: [str(e) for e in errs] for field, errs in form.errors.items()}


def _safe_redirect(request, *, default_name: str = "portfolio:portfolio"):
    next_path = (request.POST.get("next") or "").strip()
    if next_path.startswith("/") and not next_path.startswith("//"):
        return redirect(next_path)
    return redirect(reverse(default_name))


@method_decorator(require_http_methods(["POST"]), name="dispatch")
class BuyHoldingView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        form = BuyHoldingForm(request.POST)
        if not form.is_valid():
            if _wants_json(request):
                return JsonResponse(
                    {"ok": False, "errors": _form_errors_payload(form)},
                    status=400,
                )
            messages.error(request, "Could not add to portfolio.")
            return _safe_redirect(request)

        data = form.cleaned_data
        add_holding(
            request.user,
            asset_type=data["asset_type"],
            asset_name=data["asset_name"],
            app_id=data["app_id"],
            quantity=data["quantity"],
            buy_price=data["buy_price"],
        )
        if _wants_json(request):
            return JsonResponse({"ok": True})
        messages.success(request, "Added to portfolio.")
        return _safe_redirect(request)


@method_decorator(require_http_methods(["POST"]), name="dispatch")
class SellHoldingView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        form = SellHoldingForm(request.POST, user=request.user)
        if not form.is_valid():
            if _wants_json(request):
                return JsonResponse(
                    {"ok": False, "errors": _form_errors_payload(form)},
                    status=400,
                )
            messages.error(request, "Could not process sell.")
            return _safe_redirect(request)

        try:
            sell_holding(
                request.user,
                position_id=form.cleaned_data["position_id"],
                quantity=form.cleaned_data["quantity"],
                sell_price=form.cleaned_data["sell_price"],
            )
        except Portfolio.DoesNotExist:
            err = {"position_id": ["Position not found."]}
            if _wants_json(request):
                return JsonResponse({"ok": False, "errors": err}, status=400)
            messages.error(request, "Position not found.")
            return _safe_redirect(request)
        except ValueError as exc:
            err = {"__all__": [str(exc)]}
            if _wants_json(request):
                return JsonResponse({"ok": False, "errors": err}, status=400)
            messages.error(request, str(exc))
            return _safe_redirect(request)

        if _wants_json(request):
            return JsonResponse({"ok": True})
        messages.success(request, "Sale recorded.")
        return _safe_redirect(request)


@method_decorator(require_http_methods(["POST"]), name="dispatch")
class DeleteHoldingView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        form = DeleteHoldingForm(request.POST)
        if not form.is_valid():
            if _wants_json(request):
                return JsonResponse(
                    {"ok": False, "errors": _form_errors_payload(form)},
                    status=400,
                )
            messages.error(request, "Could not remove holding.")
            return _safe_redirect(request)

        try:
            delete_holding(request.user, position_id=form.cleaned_data["position_id"])
        except Portfolio.DoesNotExist:
            err = {"position_id": ["Position not found."]}
            if _wants_json(request):
                return JsonResponse({"ok": False, "errors": err}, status=400)
            messages.error(request, "Position not found.")
            return _safe_redirect(request)

        if _wants_json(request):
            return JsonResponse({"ok": True})
        messages.success(request, "Holding removed.")
        return _safe_redirect(request)


class PortfolioView(LoginRequiredMixin, TemplateView):
    template_name = "portfolio/portfolio.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_portfolio_overview_context(self.request.user))
        context["title"] = "Portfolio"
        context["active_nav"] = "portfolio"
        return context
