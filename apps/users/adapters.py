from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.users.services.antispam import rate_limit_exceeded

User = get_user_model()


class YieldVisorSocialAccountAdapter(DefaultSocialAccountAdapter):
    """OAuth login/signup aligned with YieldVisor auth UX."""

    def get_app(self, request, provider, client_id=None):
        """Prefer .env (SOCIALACCOUNT_PROVIDERS APP) over duplicate SocialApp in admin."""
        apps = self.list_apps(request, provider=provider, client_id=client_id)
        if settings.SOCIALACCOUNT_PROVIDERS.get(provider, {}).get("APP"):
            env_apps = [app for app in apps if app.pk is None]
            if env_apps:
                return env_apps[0]
        return super().get_app(request, provider, client_id=client_id)

    def get_login_redirect_url(self, request):
        next_url = request.GET.get("next") or request.POST.get("next")
        if next_url:
            return next_url
        return reverse("user:profile")

    def get_connect_redirect_url(self, request, socialaccount):
        return reverse("user:profile")

    def pre_social_login(self, request, sociallogin):
        if sociallogin.is_existing:
            return

        email = (sociallogin.user.email or "").strip()
        if not email and sociallogin.account:
            email = (sociallogin.account.extra_data.get("email") or "").strip()
        if not email:
            return

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return

        sociallogin.connect(request, user)

    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        if data.get("first_name"):
            user.first_name = data["first_name"]
        if data.get("last_name"):
            user.last_name = data["last_name"]
        return user

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        messages.success(request, f"{user.username}, Вы вошли в аккаунт")
        return user

    def is_open_for_signup(self, request, sociallogin):
        if rate_limit_exceeded(
            request,
            scope="oauth_signup",
            limit=settings.REGISTRATION_RATE_LIMIT,
        ):
            messages.error(
                request,
                "Слишком много попыток регистрации. Попробуйте позже.",
            )
            return False
        return True

    def get_signup_form_initial_data(self, request, sociallogin):
        data = super().get_signup_form_initial_data(request, sociallogin)
        extra = sociallogin.account.extra_data if sociallogin.account else {}
        if not data.get("email"):
            data["email"] = extra.get("email") or sociallogin.user.email or ""
        return data
