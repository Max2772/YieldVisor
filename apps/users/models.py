from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    image = models.ImageField(upload_to='users_images', null=True, blank=True, verbose_name='Аватар')

    class Meta:
        db_table = 'users'
        verbose_name = 'Пользователя'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.username


class UserProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
    )

    # Лимит активных алертов (аналог MAXIMUM_ALERTS из .env бота)
    max_alerts = models.PositiveSmallIntegerField(default=10)

    # Telegram-интеграция (опционально, как в боте)
    telegram_id = models.BigIntegerField(null=True, blank=True, unique=True)
    notify_telegram = models.BooleanField(default=False)

    # Email-уведомления
    notify_email = models.BooleanField(default=False)

    # Валюта отображения
    currency = models.CharField(max_length=3, default="USD")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'users_profile'
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'

    def __str__(self):
        return f"Profile({self.user.username})"

    def alerts_remaining(self) -> int:
        """Сколько алертов ещё можно создать."""
        active = self.user.alerts.filter(is_active=True).count()
        return max(0, self.max_alerts - active)

    def can_add_alert(self) -> bool:
        return self.alerts_remaining() > 0