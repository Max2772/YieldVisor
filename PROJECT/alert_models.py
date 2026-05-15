from decimal import Decimal

from django.db import models
from django.utils import timezone

from apps.portfolio.models import User, AssetType

class AlertDirection(models.TextChoices):
    GT  = ">",  "Greater than"
    GTE = ">=", "Greater than or equal"
    LT  = "<",  "Less than"
    LTE = "<=", "Less than or equal"

class Alert(models.Model):
    user         = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="alerts",
    )
    asset_type   = models.CharField(max_length=10, choices=AssetType.choices)
    asset_name   = models.CharField(max_length=255)
    app_id       = models.PositiveIntegerField(null=True, blank=True)
    target_price = models.DecimalField(max_digits=38, decimal_places=8)
    direction    = models.CharField(
        max_length=2,
        choices=AlertDirection.choices,
        default=AlertDirection.GT,
    )
    is_active    = models.BooleanField(default=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    triggered_at = models.DateTimeField(null=True, blank=True)  # когда сработал

    class Meta:
        db_table = "alerts"
        ordering = ["-created_at"]
        indexes  = [
            # Celery проверяет только активные алерты — этот индекс ускоряет запрос
            models.Index(
                fields=["is_active", "asset_type", "asset_name"],
                name="idx_alert_active_asset",
            ),
        ]

    def __str__(self):
        return f"{self.asset_name} {self.direction} {self.target_price}"

    def is_triggered(self, current_price: Decimal) -> bool:
        ops = {
            ">":  current_price >  self.target_price,
            ">=": current_price >= self.target_price,
            "<":  current_price <  self.target_price,
            "<=": current_price <= self.target_price,
        }
        return ops.get(self.direction, False)

    def trigger(self) -> None:
        """Деактивирует алерт и фиксирует время срабатывания."""
        self.is_active    = False
        self.triggered_at = timezone.now()
        self.save(update_fields=["is_active", "triggered_at"])