from django.views.generic import TemplateView

from apps.core.services.ticker import build_ticker_items


class IndexView(TemplateView):
    template_name = 'main/main.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Main'
        context['content'] = 'Main'
        context['ticker_items'] = build_ticker_items()
        return context
