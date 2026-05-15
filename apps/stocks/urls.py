from django.urls import path

from . import views

app_name = 'stocks'

urlpatterns = [
    # path('AAPL', views.StockView.as_view(), name='stock'),
    path('', views.StockMarket.as_view(), name='market'),
]
