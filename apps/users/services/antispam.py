from __future__ import annotations

import requests
from django.conf import settings
from django.core.cache import cache

from config.enums import RunMode


def get_client_ip(request) -> str:
    """Prefer Cloudflare / reverse-proxy headers when present."""
    cf_ip = request.META.get("HTTP_CF_CONNECTING_IP", "").strip()
    if cf_ip:
        return cf_ip
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "").strip()
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "") or "unknown"


def rate_limit_exceeded(
    request,
    *,
    scope: str,
    limit: int | None = None,
    window_seconds: int = 3600,
) -> bool:
    """
    Return True if the client exceeded the limit for this scope.
    Uses Django cache (Redis in PROD).
    """
    if limit is None:
        limit = settings.REGISTRATION_RATE_LIMIT
    ip = get_client_ip(request)
    key = f"auth_rl:{scope}:{ip}"
    try:
        count = cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=window_seconds)
        count = 1
    return count > limit


def verify_turnstile(request, token: str | None) -> tuple[bool, str]:
    """
    Verify Cloudflare Turnstile token.
    Skipped in DEV when keys are unset; required in PROD when secret is set.
    """
    secret = settings.TURNSTILE_SECRET_KEY
    if not secret:
        if settings.MODE.value == RunMode.PROD:
            return False, "Проверка безопасности не настроена."
        return True, ""

    if not token:
        return False, "Подтвердите, что вы не робот."

    try:
        response = requests.post(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data={
                "secret": secret,
                "response": token,
                "remoteip": get_client_ip(request),
            },
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException:
        return False, "Не удалось проверить капчу. Попробуйте позже."

    if payload.get("success"):
        return True, ""

    return False, "Проверка капчи не пройдена. Обновите страницу и попробуйте снова."
