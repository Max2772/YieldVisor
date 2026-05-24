from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class SteamView(LoginRequiredMixin, TemplateView):
    template_name = 'steam/steam.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Steam'
        context['active_nav'] = 'steam'
        return context
