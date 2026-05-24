from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class PortfolioView(LoginRequiredMixin, TemplateView):
    template_name = 'portfolio/portfolio.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Portfolio'
        context['content'] = 'PORTFOLIO'
        context['active_nav'] = 'portfolio'
        return context
