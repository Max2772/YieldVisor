from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.history.models import History, HistoryOperation
from apps.portfolio.models import Portfolio
from apps.portfolio.services.add_holding import add_holding
from apps.portfolio.services.holdings import _build_item_row, build_holdings
from apps.portfolio.types import AssetType

User = get_user_model()


class AddHoldingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="trader", password="pass")

    def test_creates_portfolio_and_history(self):
        position = add_holding(
            self.user,
            asset_type=AssetType.STOCK,
            asset_name="AMD",
            app_id=None,
            quantity=Decimal("2"),
            buy_price=Decimal("100"),
        )
        self.assertEqual(Portfolio.objects.filter(user=self.user).count(), 1)
        self.assertEqual(position.quantity, Decimal("2"))
        self.assertEqual(History.objects.filter(user=self.user).count(), 1)
        self.assertEqual(History.objects.first().operation, HistoryOperation.BUY)

    def test_averages_on_second_buy(self):
        add_holding(
            self.user,
            asset_type=AssetType.STOCK,
            asset_name="AMD",
            app_id=None,
            quantity=Decimal("2"),
            buy_price=Decimal("100"),
        )
        position = add_holding(
            self.user,
            asset_type=AssetType.STOCK,
            asset_name="AMD",
            app_id=None,
            quantity=Decimal("2"),
            buy_price=Decimal("200"),
        )
        self.assertEqual(Portfolio.objects.filter(user=self.user).count(), 1)
        self.assertEqual(position.quantity, Decimal("4"))
        self.assertEqual(position.avg_buy_price, Decimal("150"))


class BuildHoldingsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="holder", password="pass")

    def test_allocation_by_ticker(self):
        add_holding(
            self.user,
            asset_type=AssetType.STOCK,
            asset_name="NVDA",
            app_id=None,
            quantity=Decimal("2"),
            buy_price=Decimal("100"),
        )
        add_holding(
            self.user,
            asset_type=AssetType.STOCK,
            asset_name="AMD",
            app_id=None,
            quantity=Decimal("4"),
            buy_price=Decimal("50"),
        )

        _items, summary = build_holdings(self.user, AssetType.STOCK)

        self.assertEqual(len(summary["allocation"]), 2)
        labels = {s["label"] for s in summary["allocation"]}
        self.assertEqual(labels, {"NVDA", "AMD"})
        self.assertEqual(sum(s["pct"] for s in summary["allocation"]), 100)

    def test_item_row_includes_pnl_pct(self):
        position = add_holding(
            self.user,
            asset_type=AssetType.STOCK,
            asset_name="AMD",
            app_id=None,
            quantity=Decimal("2"),
            buy_price=Decimal("100"),
        )
        row = _build_item_row(position, Decimal("110"), "100,105,110")
        self.assertEqual(row["pnl_pct"], "10.0")
        self.assertTrue(row["pnl_pct_pos"])
