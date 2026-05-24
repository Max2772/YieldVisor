from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class CryptoView(LoginRequiredMixin, TemplateView):
    template_name = 'crypto/crypto.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Crypto'
        context['active_nav'] = 'crypto'
        return context
