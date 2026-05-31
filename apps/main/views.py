from django.views.generic import TemplateView

from apps.core.services.ticker import build_ticker_items
from apps.main.services.hero_mockup import build_hero_mockup_context


class IndexView(TemplateView):
    template_name = 'main/main.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Main'
        context['content'] = 'Main'
        context['ticker_items'] = build_ticker_items()
        context['hero_mockup'] = build_hero_mockup_context()
        return context
