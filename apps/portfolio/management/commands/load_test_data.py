from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models.functions import TruncMonth
from django.utils import timezone

from apps.alerts.models import Alert, AlertDirection
from apps.history.models import History, HistoryOperation
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

# (months_ago, operation, holding_index, quantity, price)
MonthlyHistorySpec = tuple[int, str, int, Decimal, Decimal]

MONTHLY_HISTORY_ROWS: list[MonthlyHistorySpec] = [
    (5, HistoryOperation.BUY, 0, Decimal("2"), Decimal("420")),
    (5, HistoryOperation.SELL, 1, Decimal("1"), Decimal("88")),
    (4, HistoryOperation.BUY, 1, Decimal("3"), Decimal("95")),
    (4, HistoryOperation.SELL, 0, Decimal("1"), Decimal("460")),
    (3, HistoryOperation.BUY, 2, Decimal("4"), Decimal("170")),
    (3, HistoryOperation.SELL, 2, Decimal("2"), Decimal("185")),
    (2, HistoryOperation.BUY, 0, Decimal("1"), Decimal("440")),
    (2, HistoryOperation.SELL, 1, Decimal("2"), Decimal("102")),
    (1, HistoryOperation.BUY, 1, Decimal("5"), Decimal("98")),
    (1, HistoryOperation.SELL, 0, Decimal("1"), Decimal("455")),
]

# demo: (months_ago, buy_qty, buy_price, sell_qty, sell_price) — one pair per calendar month
DemoMonthVolumeSpec = tuple[int, Decimal, Decimal, Decimal, Decimal]

# Balanced ~$1.2k–2.5k buy and ~$0.4k–1.1k sell per month (stocks only)
DEMO_SIX_MONTH_VOLUME: list[DemoMonthVolumeSpec] = [
    (5, Decimal("3"), Decimal("420"), Decimal("1"), Decimal("430")),
    (4, Decimal("4"), Decimal("95"), Decimal("2"), Decimal("98")),
    (3, Decimal("2"), Decimal("170"), Decimal("1"), Decimal("175")),
    (2, Decimal("2"), Decimal("440"), Decimal("1"), Decimal("455")),
    (1, Decimal("5"), Decimal("98"), Decimal("2"), Decimal("102")),
    (0, Decimal("1"), Decimal("450"), Decimal("1"), Decimal("460")),
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
                history_deleted = History.objects.filter(user=user).delete()[0]
                deleted = Portfolio.objects.filter(user=user).delete()
                Alert.objects.filter(user=user).delete()
                has_positions = False
                self.stdout.write(
                    f"  Cleared portfolio data for '{username}' "
                    f"({deleted[0]} positions, {history_deleted} history rows)"
                )

            if has_positions:
                self.stdout.write(
                    f"  Skipped holdings for '{username}' (use --clear to reload)"
                )
            else:
                self._load_holdings(user, spec["holdings"])

            if username == "demo":
                seeded = self._seed_demo_six_month_volume(user)
            else:
                seeded = self._ensure_monthly_history(user)
            if seeded:
                self.stdout.write(f"  Seeded {seeded} backdated history rows for charts")

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
                f"  -> {holdings_count} positions, {alerts_count} active alerts"
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

    def _ensure_monthly_history(self, user) -> int:
        """Backdated buy/sell rows so History monthly charts have data."""
        months_with_data = (
            History.objects.filter(user=user)
            .annotate(month=TruncMonth("created_at"))
            .values("month")
            .distinct()
            .count()
        )
        if months_with_data >= 5:
            return 0

        holdings = list(Portfolio.objects.filter(user=user).order_by("pk"))
        if not holdings:
            return 0

        tz = timezone.get_current_timezone()
        today = timezone.localdate()
        created = 0
        for months_ago, operation, holding_idx, quantity, price in MONTHLY_HISTORY_ROWS:
            holding = holdings[holding_idx % len(holdings)]
            year, month = self._shift_month(today.year, today.month, -months_ago)
            day = min(10 + holding_idx, 28)
            when = timezone.make_aware(datetime(year, month, day, 12, 0), tz)
            self._create_backdated_history(
                user,
                holding=holding,
                operation=operation,
                quantity=quantity,
                price=price,
                when=when,
            )
            created += 1
        return created

    def _shift_month(self, year: int, month: int, delta: int) -> tuple[int, int]:
        month += delta
        while month <= 0:
            month += 12
            year -= 1
        while month > 12:
            month -= 12
            year += 1
        return year, month

    def _create_backdated_history(
        self,
        user,
        *,
        holding: Portfolio,
        operation: str,
        quantity: Decimal,
        price: Decimal,
        when: datetime,
    ) -> None:
        row = History.objects.create(
            user=user,
            portfolio=holding if operation == HistoryOperation.BUY else None,
            operation=operation,
            asset_type=holding.asset_type,
            asset_name=holding.asset_name,
            app_id=holding.app_id,
            quantity=quantity,
            price=price,
        )
        History.objects.filter(pk=row.pk).update(created_at=when)

    def _demo_chart_seed_day(self, index: int) -> int:
        return 5 + index

    def _seed_demo_six_month_volume(self, user) -> int:
        """Fill each of the last 6 months with balanced buy/sell rows for Monthly Volume."""
        stock_holdings = [
            h for h in Portfolio.objects.filter(user=user).order_by("pk")
            if h.asset_type == AssetType.STOCK
        ]
        if not stock_holdings:
            return 0

        tz = timezone.get_current_timezone()
        today = timezone.localdate()
        created = 0

        for index, (months_ago, buy_qty, buy_price, sell_qty, sell_price) in enumerate(
            DEMO_SIX_MONTH_VOLUME,
        ):
            year, month = self._shift_month(today.year, today.month, -months_ago)
            seed_day = self._demo_chart_seed_day(index)

            month_filter = History.objects.filter(
                user=user,
                created_at__year=year,
                created_at__month=month,
            )
            if months_ago > 0:
                month_filter.delete()
            else:
                month_filter.filter(created_at__day=seed_day).delete()

            holding_buy = stock_holdings[index % len(stock_holdings)]
            holding_sell = stock_holdings[(index + 1) % len(stock_holdings)]

            when_buy = timezone.make_aware(
                datetime(year, month, seed_day, 10, 30),
                tz,
            )
            self._create_backdated_history(
                user,
                holding=holding_buy,
                operation=HistoryOperation.BUY,
                quantity=buy_qty,
                price=buy_price,
                when=when_buy,
            )
            created += 1

            when_sell = timezone.make_aware(
                datetime(year, month, seed_day, 15, 45),
                tz,
            )
            self._create_backdated_history(
                user,
                holding=holding_sell,
                operation=HistoryOperation.SELL,
                quantity=sell_qty,
                price=sell_price,
                when=when_sell,
            )
            created += 1

        return created
