"""
OAuth-only URLconf for django-allauth.

Exposes provider login/callback endpoints only. No allauth account UI
(login, signup, email, password reset, connections, etc.).
"""

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import include, path


def _redirect_login(request, message=None, level=messages.ERROR):
    if message:
        getattr(messages, level)(request, message)
    return redirect("user:login")


def oauth_login_cancelled(request):
    return _redirect_login(request, "Вход через соцсеть отменён", messages.INFO)


def oauth_login_error(request):
    return _redirect_login(request, "Не удалось войти через соцсеть. Попробуйте снова.")


def oauth_signup_fallback(request):
    messages.warning(
        request,
        "Дополните регистрацию по email или войдите существующим аккаунтом.",
    )
    return redirect("user:registration")


urlpatterns = [
    # /accounts/ and /accounts/connections/ are intentionally omitted (404).
    path(
        "login/cancelled/",
        oauth_login_cancelled,
        name="socialaccount_login_cancelled",
    ),
    path("login/error/", oauth_login_error, name="socialaccount_login_error"),
    path("signup/", oauth_signup_fallback, name="socialaccount_signup"),
    path("", include("allauth.socialaccount.providers.google.urls")),
    path("", include("allauth.socialaccount.providers.github.urls")),
]
