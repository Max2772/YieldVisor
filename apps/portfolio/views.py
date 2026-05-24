from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from apps.portfolio.services.portfolio_overview import build_portfolio_overview_context


class PortfolioView(LoginRequiredMixin, TemplateView):
    template_name = 'portfolio/portfolio.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_portfolio_overview_context(self.request.user))
        context['title'] = 'Portfolio'
        context['active_nav'] = 'portfolio'
        return context
