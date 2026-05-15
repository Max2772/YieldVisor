from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db import models

from apps.portfolio.types import AssetType

User = get_user_model()


class Portfolio(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="portfolio",
    )
    asset_type = models.CharField(
        max_length=10,
        choices=AssetType.choices,
    )
    asset_name = models.CharField(max_length=255)  # "NVDA", "BTC", "Glove Case"
    app_id = models.PositiveIntegerField(  # только для Steam (730 = CS2)
        null=True, blank=True,
    )
    quantity = models.DecimalField(
        max_digits=38, decimal_places=8,
        validators=[MinValueValidator(Decimal("0"))],
    )
    avg_buy_price = models.DecimalField(  # средневзвешенная цена покупки
        max_digits=38, decimal_places=2,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "portfolios"
        ordering = ["asset_type", "asset_name"]
        constraints = [
            # Для Steam: уникальность по (user, type, name, app_id)
            models.UniqueConstraint(
                fields=["user", "asset_type", "asset_name", "app_id"],
                condition=models.Q(app_id__isnull=False),
                name="unique_portfolio_with_app_id",
            ),
            # Для stocks/crypto: app_id всегда NULL → отдельное ограничение
            # (в SQL NULL != NULL, поэтому unique_together не работает)
            models.UniqueConstraint(
                fields=["user", "asset_type", "asset_name"],
                condition=models.Q(app_id__isnull=True),
                name="unique_portfolio_without_app_id",
            ),
        ]

    def __str__(self):
        return f"{self.asset_name} × {self.quantity} (user={self.user_id})"

    # ── Вычисляемые свойства ──────────────────────────────────────────

    def cost_basis(self) -> Decimal:
        """Сколько вложено: qty × avg_buy."""
        return self.quantity * self.avg_buy_price

    def pnl(self, current_price: Decimal) -> Decimal:
        """Нереализованный P&L при известной текущей цене."""
        return (current_price - self.avg_buy_price) * self.quantity

    def pnl_pct(self, current_price: Decimal) -> Decimal:
        """P&L в процентах."""
        if not self.avg_buy_price:
            return Decimal("0")
        return ((current_price - self.avg_buy_price) / self.avg_buy_price) * 100

    def current_value(self, current_price: Decimal) -> Decimal:
        return self.quantity * current_price
