from django.urls import path

from apps.portfolio.views import MarketSearchView

from . import views

app_name = 'stocks'

urlpatterns = [
    path('', views.StockMarket.as_view(), name='market'),
    path('market-search/', MarketSearchView.as_view(), name='market_search'),
    path('<str:ticker>/', views.StockView.as_view(), name='stock'),
]
