from django.urls import path

from apps.portfolio.views import MarketSearchView

from . import views

app_name = 'steam'

urlpatterns = [
    path('', views.SteamView.as_view(), name='steam'),
    path('market-search/', MarketSearchView.as_view(), name='market_search'),
    path(
        '<int:app_id>/<str:market_hash_name>/',
        views.SteamItemView.as_view(),
        name='item',
    ),
]
