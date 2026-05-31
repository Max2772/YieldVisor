from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.history.models import History, HistoryOperation
from apps.history.services.history_page import build_history_page_context
from apps.portfolio.services.add_holding import add_holding
from apps.portfolio.services.holding_actions import sell_holding
from apps.portfolio.types import AssetType

User = get_user_model()


class HistoryPageContextTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="historian", password="pass")

    def test_empty_user_context(self):
        ctx = build_history_page_context(self.user, params={})
        self.assertEqual(ctx["total_txns"], 0)
        self.assertEqual(ctx["buy_count"], 0)
        self.assertEqual(ctx["history"], [])

    def test_summaries_after_buy_and_sell(self):
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

        ctx = build_history_page_context(self.user, params={})
        self.assertEqual(ctx["total_txns"], 2)
        self.assertEqual(ctx["buy_count"], 1)
        self.assertEqual(ctx["sell_count"], 1)
        self.assertEqual(ctx["realised_pnl_dollars"], "80")
        self.assertEqual(len(ctx["history"]), 2)
        self.assertEqual(len(ctx["history_export"]), 2)
        self.assertIn("detail_url", ctx["history"][0])
        self.assertNotIn(",", ctx["history_export"][0]["total"])

    def test_filter_by_operation(self):
        add_holding(
            self.user,
            asset_type=AssetType.CRYPTO,
            asset_name="BTC",
            app_id=None,
            quantity=Decimal("1"),
            buy_price=Decimal("50000"),
        )
        ctx = build_history_page_context(
            self.user,
            params={"op": HistoryOperation.SELL},
        )
        self.assertEqual(ctx["page_obj"].paginator.count, 0)
        self.assertEqual(ctx["history"], [])


class HistoryViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="viewer", password="pass")
        self.client.login(username="viewer", password="pass")

    def test_page_renders_without_hardcoded_rows(self):
        response = self.client.get(reverse("history:history"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "BT</div>")
        self.assertContains(response, "No transactions match your filters.")
