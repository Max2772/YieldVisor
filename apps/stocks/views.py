from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class StockMarket(LoginRequiredMixin, TemplateView):
    template_name = 'stocks/stocks.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Stocks'
        context['active_nav'] = 'stocks'
        return context


class StockView(LoginRequiredMixin, TemplateView):
    """Страница отдельной бумаги (позже)."""
    template_name = 'stocks/stock.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Stock'
        context['active_nav'] = 'stocks'
        return context
