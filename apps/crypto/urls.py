from django.urls import path

from . import views

app_name = 'crypto'

urlpatterns = [
    path('', views.CryptoView.as_view(), name='crypto'),
]
