from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class AnalyticsView(LoginRequiredMixin, TemplateView):
    template_name = 'analytics/analytics.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Analytics'
        context['content'] = 'ANALYTICS'
        return context
