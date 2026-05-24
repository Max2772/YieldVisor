from django.urls import path

from . import views

app_name = 'crypto'

urlpatterns = [
    path('', views.CryptoView.as_view(), name='crypto'),
    path('<str:coin>/', views.CryptoCoinView.as_view(), name='coin'),
]
