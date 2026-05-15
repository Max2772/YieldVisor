from django.urls import path

from . import views

app_name = 'portfolio'

urlpatterns = [
    path('', views.PortfolioView.as_view(), name='portfolio'),
]
