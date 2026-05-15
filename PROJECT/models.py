from decimal import Decimal

from django.db import models

from apps.portfolio.models import User, Portfolio, AssetType


class HistoryOperation(models.TextChoices):
    BUY  = "buy",  "Buy"
    SELL = "sell", "Sell"


class History(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="history",
    )
    portfolio  = models.ForeignKey(
        Portfolio,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="history",
    )
    operation  = models.CharField(max_length=4, choices=HistoryOperation.choices)
    asset_type = models.CharField(max_length=10, choices=AssetType.choices)
    asset_name = models.CharField(max_length=255)
    app_id     = models.PositiveIntegerField(null=True, blank=True)
    quantity   = models.DecimalField(max_digits=38, decimal_places=8)
    price      = models.DecimalField(                # фактическая цена сделки
        max_digits=38, decimal_places=2,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "history"

        ordering = ["-created_at"]
        indexes  = [
            # Частый запрос: история юзера с фильтром по типу актива
            models.Index(
                fields=["user", "asset_type", "-created_at"],
                name="idx_history_user_type_date",
            ),
        ]

    def __str__(self):
        return f"{self.operation.upper()} {self.quantity} {self.asset_name} @ {self.price}"

    @property
    def total(self) -> Decimal:
        return self.quantity * self.price
