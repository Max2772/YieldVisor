from django.urls import path

from . import views

app_name = 'stocks'

urlpatterns = [
    path('stock/', views.StockView.as_view(), name='stock'),
    path('stocks/', views.StockMarket.as_view(), name='market'),
]
