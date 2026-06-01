import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models.signals import post_migrate, post_save
from django.dispatch import receiver

from .models import UserProfile

User = get_user_model()


def _normalize_site_domain(domain: str) -> str:
    domain = domain.strip()
    for prefix in ("https://", "http://"):
        if domain.startswith(prefix):
            domain = domain[len(prefix):]
    return domain.rstrip("/")


def ensure_site_domain() -> None:
    """Sync django.contrib.sites.Site from SITE_DOMAIN / SITE_ID in settings."""
    configured = getattr(settings, "SITE_DOMAIN", None) or os.getenv("SITE_DOMAIN", "")
    if not configured and settings.DEBUG:
        configured = "127.0.0.1:8000"
    if not configured:
        return

    from django.contrib.sites.models import Site

    domain = _normalize_site_domain(configured)
    site_id = settings.SITE_ID

    if Site.objects.filter(pk=site_id).exists():
        Site.objects.filter(pk=site_id).update(domain=domain, name="YieldVisor")
        return

    # SITE_ID row missing but another Site already uses this domain (common after SITE_ID change).
    Site.objects.filter(domain=domain).exclude(pk=site_id).delete()
    Site.objects.create(pk=site_id, domain=domain, name="YieldVisor")


@receiver(post_migrate)
def sync_site_after_migrate(sender, **kwargs):
    if sender.name not in ("sites", "users"):
        return
    ensure_site_domain()


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)
