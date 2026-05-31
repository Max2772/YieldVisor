from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from apps.analytics.services.analytics_page import build_analytics_context
from apps.analytics.services.metric_help import METRIC_HELP


class AnalyticsView(LoginRequiredMixin, TemplateView):
    template_name = 'analytics/analytics.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_nav'] = 'analytics'
        context['title'] = 'Analytics'
        context.update(build_analytics_context(self.request.user))
        context["metric_help"] = METRIC_HELP
        return context
