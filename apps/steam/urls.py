from django.urls import path

from . import views

app_name = 'steam'

urlpatterns = [
    path('', views.SteamView.as_view(), name='steam'),
    path(
        '<int:app_id>/<str:market_hash_name>/',
        views.SteamItemView.as_view(),
        name='item',
    ),
]
