from django.views.generic import TemplateView

from apps.core.services.ticker import build_ticker_items
from apps.main.services.hero_mockup import build_hero_mockup_context


def _pub_nav_actions_for_request(request) -> list[dict[str, str]]:
    if request.user.is_authenticated:
        return [
            {
                "label": "Analytics",
                "url_name": "analytics:analytics",
                "btn_class": "btn-ghost",
            },
            {
                "label": "Portfolio →",
                "url_name": "portfolio:portfolio",
                "btn_class": "btn-primary",
            },
        ]
    return [
        {
            "label": "Log in",
            "url_name": "user:login",
            "btn_class": "btn-ghost",
        },
        {
            "label": "Get started →",
            "url_name": "user:registration",
            "btn_class": "btn-primary",
        },
    ]


class IndexView(TemplateView):
    template_name = 'main/main.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Main'
        context['content'] = 'Main'
        context['ticker_items'] = build_ticker_items()
        context['hero_mockup'] = build_hero_mockup_context()
        context['pub_nav_actions'] = _pub_nav_actions_for_request(self.request)
        return context
