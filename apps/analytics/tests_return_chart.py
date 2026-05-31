from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from apps.analytics.services.return_chart import (
    _benchmark_pct_points,
    _history_fetch_days,
)
from apps.core.services.invest_api import PriceHistory, PriceHistoryPoint


class BenchmarkChartTests(SimpleTestCase):
    def test_history_fetch_days_covers_portfolio_span(self):
        days = ["2024-01-01", "2024-06-01", "2024-12-01"]
        self.assertGreaterEqual(_history_fetch_days(days, 30), 345)

    @patch("apps.analytics.services.return_chart.get_history")
    def test_benchmark_aligns_to_portfolio_timestamps(self, mock_get_history):
        mock_get_history.return_value = PriceHistory(
            asset_type="stock",
            name="SPY",
            points=(
                PriceHistoryPoint(timestamp="2024-01-01T00:00:00", price=Decimal("400")),
                PriceHistoryPoint(timestamp="2024-01-02T00:00:00", price=Decimal("404")),
                PriceHistoryPoint(timestamp="2024-01-03T00:00:00", price=Decimal("396")),
            ),
        )
        timestamps = [
            "2023-12-31T00:00:00",
            "2024-01-02T00:00:00",
            "2024-01-03T00:00:00",
        ]
        client = MagicMock()
        points = _benchmark_pct_points(timestamps, client, fetch_days=30)

        self.assertEqual(len(points), 3)
        self.assertEqual(points[0]["t"], timestamps[0])
        self.assertEqual(points[0]["v"], 0.0)
        self.assertEqual(points[1]["v"], 1.0)
        self.assertEqual(points[2]["v"], -1.0)
