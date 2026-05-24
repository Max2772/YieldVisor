from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.history.models import History, HistoryOperation
from apps.portfolio.models import Portfolio
from apps.portfolio.services.add_holding import add_holding
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
