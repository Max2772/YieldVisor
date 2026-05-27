from django.urls import path

from . import views

app_name = 'portfolio'

urlpatterns = [
    path('', views.PortfolioView.as_view(), name='portfolio'),
    path('holding/buy/', views.BuyHoldingView.as_view(), name='buy_holding'),
    path('holding/sell/', views.SellHoldingView.as_view(), name='sell_holding'),
    path('holding/delete/', views.DeleteHoldingView.as_view(), name='delete_holding'),
]
