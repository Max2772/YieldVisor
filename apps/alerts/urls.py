from django.urls import path

from . import views

app_name = 'alerts'

urlpatterns = [
    path('', views.AlertsView.as_view(), name='alerts'),
    path('create/', views.CreateAlertView.as_view(), name='create'),
    path('<int:pk>/delete/', views.DeleteAlertView.as_view(), name='delete'),
]
