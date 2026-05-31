from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from apps.history.services.history_page import build_history_page_context


class HistoryView(LoginRequiredMixin, TemplateView):
    template_name = "history/history.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "History"
        context["content"] = "HISTORY"
        context["active_nav"] = "history"
        context.update(build_history_page_context(
            self.request.user,
            params=self.request.GET,
        ))
        return context
