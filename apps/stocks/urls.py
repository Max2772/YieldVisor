from django.urls import path

from . import views

app_name = 'stocks'

urlpatterns = [
    path('', views.StockMarket.as_view(), name='market'),
    path('<str:ticker>/', views.StockView.as_view(), name='stock'),
]
