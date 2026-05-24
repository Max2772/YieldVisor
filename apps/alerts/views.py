from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class AlertsView(LoginRequiredMixin, TemplateView):
    template_name = 'alerts/alerts.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Alerts'
        context['content'] = 'ALERTS'
        context['active_nav'] = 'alerts'
        return context
