from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase

from apps.core.market_catalog import (
    CRYPTO_MARKET_CATALOG,
    STOCK_MARKET_CATALOG,
    STEAM_MARKET_CATALOG,
    pick_crypto_catalog,
    pick_stock_catalog,
    pick_steam_catalog,
)
from apps.portfolio.services.holdings import _build_value_allocation

User = get_user_model()


class MarketCatalogTests(SimpleTestCase):
    def test_pick_returns_subset(self):
        picked = pick_stock_catalog(2)
        self.assertEqual(len(picked), 2)
        self.assertTrue(all(entry in STOCK_MARKET_CATALOG for entry in picked))

    def test_pick_crypto_and_steam(self):
        self.assertEqual(len(pick_crypto_catalog(2)), 2)
        self.assertEqual(len(pick_steam_catalog(2)), 2)
        self.assertGreater(len(CRYPTO_MARKET_CATALOG), 2)
        self.assertGreater(len(STEAM_MARKET_CATALOG), 2)


class AllocationTests(SimpleTestCase):
    def test_allocation_sums_to_100(self):
        items = [
            {"ticker": "A", "_total_raw": Decimal("60")},
            {"ticker": "B", "_total_raw": Decimal("40")},
        ]
        allocation = _build_value_allocation(items, Decimal("100"))
        self.assertEqual(sum(s["pct"] for s in allocation), 100)
        self.assertEqual(allocation[0]["label"], "A")
