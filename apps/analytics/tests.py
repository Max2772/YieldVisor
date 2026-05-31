from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.analytics.services.analytics_page import build_analytics_context
from apps.analytics.services.metrics import (
    daily_returns,
    max_drawdown,
    monthly_returns,
    notable_days,
    to_cumulative_pct,
)
from apps.portfolio.models import Portfolio
from apps.portfolio.types import AssetType

User = get_user_model()


class AnalyticsMathTests(TestCase):
    def test_cumulative_pct_from_first_point(self):
        values = [100.0, 110.0, 105.0]
        self.assertEqual(to_cumulative_pct(values), [0.0, 10.0, 5.0])

    def test_max_drawdown_finds_trough(self):
        days = ["2026-01-01", "2026-01-02", "2026-01-03"]
        values = [100.0, 120.0, 90.0]
        drawdown, trough_day = max_drawdown(days, values)
        self.assertEqual(drawdown, Decimal("25.0"))
        self.assertEqual(trough_day, "2026-01-03")

    def test_notable_days_and_win_rate(self):
        days = ["2026-01-01", "2026-01-02", "2026-01-03", "2026-01-04"]
        values = [100.0, 110.0, 99.0, 105.0]
        notable = notable_days(days, values)
        self.assertEqual(notable["best_day_pct"], "10.0")
        self.assertEqual(notable["worst_day_pct"], "10.0")
        self.assertEqual(notable["win_rate"], 66)

    def test_monthly_returns(self):
        days = [
            "2026-01-15", "2026-01-31",
            "2026-02-10", "2026-02-28",
        ]
        values = [100.0, 110.0, 110.0, 121.0]
        labels, returns = monthly_returns(days, values)
        self.assertEqual(labels, ["Feb"])
        self.assertEqual(returns, [10.0])

    def test_daily_returns(self):
        self.assertEqual(daily_returns([100.0, 110.0, 99.0]), [0.1, -0.1])


class AnalyticsContextTests(TestCase):
    def test_empty_portfolio_context(self):
        user = User.objects.create_user(username="analytics-empty", password="pass")
        ctx = build_analytics_context(user)
        self.assertFalse(ctx["has_data"])
        self.assertEqual(ctx["asset_breakdown"], [])
        self.assertEqual(ctx["allocation"], [])

    @patch("apps.analytics.services.analytics_page.build_return_chart")
    @patch("apps.analytics.services.analytics_page._fetch_market_data")
    @patch("apps.analytics.services.analytics_page._build_portfolio_chart")
    @patch("apps.analytics.services.analytics_page.InvestAPIClient")
    def test_builds_breakdown_from_holdings(
        self,
        mock_client_cls,
        mock_build_chart,
        mock_fetch_market,
        mock_return_chart,
    ):
        user = User.objects.create_user(username="analytics-user", password="pass")
        position = Portfolio.objects.create(
            user=user,
            asset_type=AssetType.STOCK,
            asset_name="NVDA",
            quantity=Decimal("2"),
            avg_buy_price=Decimal("100"),
        )
        mock_client_cls.return_value.__enter__.return_value = object()
        mock_build_chart.return_value = {"points": []}
        mock_return_chart.return_value = {"series": {}, "benchmark": [], "filters": []}
        mock_fetch_market.return_value = [
            (position, Decimal("120"), "100,120", "NVIDIA", ""),
        ]

        ctx = build_analytics_context(user)

        self.assertTrue(ctx["has_data"])
        self.assertEqual(len(ctx["asset_breakdown"]), 1)
        self.assertEqual(ctx["asset_breakdown"][0]["ticker"], "NVDA")
        self.assertEqual(ctx["total_return_pct"], "20.0")
        self.assertEqual(len(ctx["allocation"]), 1)
        self.assertEqual(ctx["allocation"][0]["name"], "Stocks")
