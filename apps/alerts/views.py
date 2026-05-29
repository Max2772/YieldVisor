from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods
from django.views.generic import TemplateView, View

from apps.alerts.forms import CreateAlertForm, DeleteAlertForm
from apps.alerts.models import Alert
from apps.alerts.services.alerts_page import build_alerts_page_context, create_alert


def _wants_json(request) -> bool:
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def _form_errors_payload(form) -> dict[str, list[str]]:
    return {field: [str(e) for e in errs] for field, errs in form.errors.items()}


def _safe_redirect(request, *, default_name: str = "alerts:alerts"):
    next_path = (request.POST.get("next") or "").strip()
    if next_path.startswith("/") and not next_path.startswith("//"):
        return redirect(next_path)
    return redirect(reverse(default_name))


class AlertsView(LoginRequiredMixin, TemplateView):
    template_name = "alerts/alerts.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Alerts"
        context["content"] = "ALERTS"
        context["active_nav"] = "alerts"
        context.update(build_alerts_page_context(self.request.user))
        return context


@method_decorator(require_http_methods(["POST"]), name="dispatch")
class CreateAlertView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        form = CreateAlertForm(request.POST)
        if not form.is_valid():
            if _wants_json(request):
                return JsonResponse(
                    {"ok": False, "errors": _form_errors_payload(form)},
                    status=400,
                )
            err = next(
                (msg for errs in form.errors.values() for msg in errs),
                None,
            )
            messages.error(request, err or "Could not create alert.")
            return _safe_redirect(request)

        create_alert(
            request.user,
            asset_type=form.cleaned_data["asset_type"],
            asset_name=form.cleaned_data["asset_name"],
            app_id=form.cleaned_data.get("app_id"),
            direction=form.cleaned_data["direction"],
            target_price=form.cleaned_data["target_price"],
        )
        messages.success(request, "Alert created.")
        return _safe_redirect(request)


@method_decorator(require_http_methods(["POST"]), name="dispatch")
class DeleteAlertView(LoginRequiredMixin, View):
    def post(self, request, pk: int, *args, **kwargs):
        form = DeleteAlertForm(request.POST)
        if not form.is_valid():
            if _wants_json(request):
                return JsonResponse(
                    {"ok": False, "errors": _form_errors_payload(form)},
                    status=400,
                )
            messages.error(request, "Could not delete alert.")
            return _safe_redirect(request)

        deleted, _ = Alert.objects.filter(user=request.user, pk=pk).delete()
        if not deleted:
            if _wants_json(request):
                return JsonResponse(
                    {"ok": False, "errors": {"__all__": ["Alert not found."]}},
                    status=404,
                )
            messages.error(request, "Alert not found.")
            return _safe_redirect(request)

        if _wants_json(request):
            return JsonResponse({"ok": True})
        messages.success(request, "Alert deleted.")
        return _safe_redirect(request)
