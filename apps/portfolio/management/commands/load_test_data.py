from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.alerts.models import Alert, AlertDirection
from apps.portfolio.models import Portfolio
from apps.portfolio.services.add_holding import add_holding
from apps.portfolio.types import AssetType

User = get_user_model()

DEFAULT_PASSWORD = "testpass123"

HoldingSpec = tuple[str, str, int | None, Decimal, Decimal]

TEST_USERS: list[dict[str, Any]] = [
    {
        "username": "demo",
        "email": "demo@yieldvisor.local",
        "first_name": "Demo",
        "holdings": [
            (AssetType.STOCK, "NVDA", None, Decimal("3"), Decimal("450")),
            (AssetType.STOCK, "AMD", None, Decimal("10"), Decimal("95")),
            (AssetType.STOCK, "AAPL", None, Decimal("5"), Decimal("175")),
            (AssetType.CRYPTO, "bitcoin", None, Decimal("0.05"), Decimal("62000")),
            (AssetType.CRYPTO, "ethereum", None, Decimal("0.7"), Decimal("2100")),
            (AssetType.STEAM, "AK-47 | Redline (Field-Tested)", 730, Decimal("1"), Decimal("45")),
            (AssetType.STEAM, "AWP | Asiimov (Field-Tested)", 730, Decimal("1"), Decimal("120")),
        ],
        "alerts": [
            (AssetType.STOCK, "NVDA", None, Decimal("900"), AlertDirection.GT),
            (AssetType.CRYPTO, "bitcoin", None, Decimal("70000"), AlertDirection.GTE),
        ],
    },
    {
        "username": "alice",
        "email": "alice@yieldvisor.local",
        "first_name": "Alice",
        "holdings": [
            (AssetType.STOCK, "MSFT", None, Decimal("4"), Decimal("380")),
            (AssetType.STOCK, "GOOGL", None, Decimal("2"), Decimal("140")),
            (AssetType.STOCK, "META", None, Decimal("1"), Decimal("480")),
        ],
        "alerts": [],
    },
    {
        "username": "bob",
        "email": "bob@yieldvisor.local",
        "first_name": "Bob",
        "holdings": [
            (AssetType.CRYPTO, "solana", None, Decimal("12"), Decimal("140")),
            (AssetType.CRYPTO, "cardano", None, Decimal("500"), Decimal("0.55")),
            (AssetType.STEAM, "Glove Case", 730, Decimal("3"), Decimal("12")),
        ],
        "alerts": [
            (AssetType.CRYPTO, "solana", None, Decimal("200"), AlertDirection.LT),
        ],
    },
]


class Command(BaseCommand):
    help = "Create test users with sample portfolio holdings and alerts."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            default=DEFAULT_PASSWORD,
            help=f"Password for all test users (default: {DEFAULT_PASSWORD}).",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Remove existing portfolio, history, and alerts for test users before loading.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        password: str = options["password"]
        clear: bool = options["clear"]

        for spec in TEST_USERS:
            username = spec["username"]
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": spec["email"],
                    "first_name": spec["first_name"],
                },
            )
            if created:
                user.set_password(password)
                user.save(update_fields=["password"])
                self.stdout.write(self.style.SUCCESS(f"Created user '{username}'"))
            else:
                user.email = spec["email"]
                user.first_name = spec["first_name"]
                user.set_password(password)
                user.save(update_fields=["email", "first_name", "password"])
                self.stdout.write(f"Updated user '{username}'")

            has_positions = Portfolio.objects.filter(user=user).exists()

            if clear:
                deleted = Portfolio.objects.filter(user=user).delete()
                Alert.objects.filter(user=user).delete()
                has_positions = False
                self.stdout.write(
                    f"  Cleared portfolio data for '{username}' ({deleted[0]} rows)"
                )

            if has_positions:
                self.stdout.write(
                    f"  Skipped holdings for '{username}' (use --clear to reload)"
                )
            else:
                self._load_holdings(user, spec["holdings"])

            for asset_type, asset_name, app_id, target, direction in spec["alerts"]:
                Alert.objects.get_or_create(
                    user=user,
                    asset_type=asset_type,
                    asset_name=asset_name,
                    app_id=app_id,
                    target_price=target,
                    direction=direction,
                    defaults={"is_active": True},
                )

            holdings_count = Portfolio.objects.filter(user=user).count()
            alerts_count = Alert.objects.filter(user=user, is_active=True).count()
            self.stdout.write(
                f"  → {holdings_count} positions, {alerts_count} active alerts"
            )

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Test data loaded."))
        self.stdout.write(f"Password for all users: {password}")
        self.stdout.write("Users: " + ", ".join(u["username"] for u in TEST_USERS))

    def _load_holdings(self, user, holdings: list[HoldingSpec]) -> None:
        for asset_type, asset_name, app_id, qty, price in holdings:
            add_holding(
                user,
                asset_type=asset_type,
                asset_name=asset_name,
                app_id=app_id,
                quantity=qty,
                buy_price=price,
            )
