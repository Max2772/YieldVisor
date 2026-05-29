from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from apps.history.models import History, HistoryOperation
from apps.portfolio.models import Portfolio
from apps.portfolio.forms import BuyHoldingForm, SellHoldingForm
from apps.portfolio.services.add_holding import add_holding
from apps.portfolio.services.holding_actions import delete_holding, sell_holding
from apps.portfolio.services.holdings import _build_item_row, build_holdings
from apps.portfolio.types import AssetType

User = get_user_model()


class MarketSearchViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="searcher", password="pass")
        self.client.login(username="searcher", password="pass")

    @patch("apps.portfolio.views.InvestAPIClient")
    def test_returns_api_results(self, client_cls):
        api = client_cls.return_value.__enter__.return_value
        api.search.return_value = {
            "query": "nvda",
            "results": [
                {
                    "asset_type": "stock",
                    "name": "NVDA",
                    "full_name": "NVIDIA Corporation",
                }
            ],
        }

        response = self.client.get(
            reverse("stocks:market_search"),
            {"q": "nvda", "type": "stock"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["results"]), 1)
        api.search.assert_called_once_with("nvda", "stock", limit=5)


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


class SellDeleteHoldingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="seller", password="pass")

    def test_sell_partial_keeps_position(self):
        pos = add_holding(
            self.user,
            asset_type=AssetType.STOCK,
            asset_name="AMD",
            app_id=None,
            quantity=Decimal("10"),
            buy_price=Decimal("100"),
        )
        sell_holding(
            self.user,
            position_id=pos.pk,
            quantity=Decimal("4"),
            sell_price=Decimal("120"),
        )
        pos.refresh_from_db()
        self.assertEqual(pos.quantity, Decimal("6"))
        self.assertEqual(
            History.objects.filter(user=self.user, operation=HistoryOperation.SELL).count(),
            1,
        )

    def test_sell_all_deletes_position(self):
        pos = add_holding(
            self.user,
            asset_type=AssetType.STOCK,
            asset_name="AMD",
            app_id=None,
            quantity=Decimal("2"),
            buy_price=Decimal("100"),
        )
        sell_holding(
            self.user,
            position_id=pos.pk,
            quantity=Decimal("2"),
            sell_price=Decimal("110"),
        )
        self.assertEqual(Portfolio.objects.filter(user=self.user).count(), 0)
        self.assertEqual(History.objects.filter(user=self.user).count(), 2)

    def test_delete_removes_position(self):
        pos = add_holding(
            self.user,
            asset_type=AssetType.STOCK,
            asset_name="NVDA",
            app_id=None,
            quantity=Decimal("1"),
            buy_price=Decimal("500"),
        )
        delete_holding(self.user, position_id=pos.pk)
        self.assertEqual(Portfolio.objects.filter(user=self.user).count(), 0)

    def test_delete_keeps_history_without_portfolio_link(self):
        pos = add_holding(
            self.user,
            asset_type=AssetType.STOCK,
            asset_name="NVDA",
            app_id=None,
            quantity=Decimal("1"),
            buy_price=Decimal("500"),
        )
        history_id = History.objects.get(portfolio=pos).pk
        delete_holding(self.user, position_id=pos.pk)
        history = History.objects.get(pk=history_id)
        self.assertIsNone(history.portfolio_id)

    def test_steam_buy_rejects_fractional_quantity(self):
        form = BuyHoldingForm(
            {
                "asset_type": AssetType.STEAM,
                "asset_name": "AWP | Asiimov (Field-Tested)",
                "app_id": 730,
                "quantity": "1.5",
                "buy_price": "100",
            },
        )
        self.assertFalse(form.is_valid())
        self.assertTrue(form.errors.get("quantity"))

    def test_steam_sell_rejects_fractional_quantity(self):
        pos = add_holding(
            self.user,
            asset_type=AssetType.STEAM,
            asset_name="AWP | Asiimov (Field-Tested)",
            app_id=730,
            quantity=Decimal("2"),
            buy_price=Decimal("100"),
        )
        form = SellHoldingForm(
            {
                "position_id": pos.pk,
                "quantity": "0.5",
                "sell_price": "120",
            },
            user=self.user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("quantity", form.errors)


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
        self.assertEqual(row["position_id"], position.pk)
        self.assertEqual(row["asset_name"], "AMD")
        self.assertEqual(row["asset_type"], AssetType.STOCK)
        self.assertIn("qty_raw", row)


class BuyHoldingAjaxTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="buyer", password="pass")
        self.client = Client()
        self.client.login(username="buyer", password="pass")

    def test_buy_returns_json_ok(self):
        r = self.client.post(
            reverse("portfolio:buy_holding"),
            {
                "asset_type": AssetType.STOCK,
                "asset_name": "GOOG",
                "quantity": "1",
                "buy_price": "100.00",
                "next": "/stocks/",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["ok"])
        self.assertEqual(Portfolio.objects.filter(user=self.user).count(), 1)
