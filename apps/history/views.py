from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class HistoryView(LoginRequiredMixin, TemplateView):
    template_name = 'history/history.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'History'
        context['content'] = 'HISTORY'
        return context
