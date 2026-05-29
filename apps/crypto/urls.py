from django.urls import path

from apps.portfolio.views import MarketSearchView

from . import views

app_name = 'crypto'

urlpatterns = [
    path('', views.CryptoView.as_view(), name='crypto'),
    path('market-search/', MarketSearchView.as_view(), name='market_search'),
    path('<str:coin>/', views.CryptoCoinView.as_view(), name='coin'),
]
