from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import SimpleTestCase, TestCase

from apps.main.services.hero_mockup import (
    HERO_QUANTITY,
    HERO_STEAM_NAME,
    _hero_assets,
    build_hero_mockup_context,
)
from apps.portfolio.types import AssetType


class HeroAssetsTests(SimpleTestCase):
    def test_fixed_assets_in_stock_crypto_steam_order(self):
        assets = _hero_assets()

        self.assertEqual(len(assets), 3)
        self.assertEqual(assets[0]["asset_type"], AssetType.STOCK)
        self.assertEqual(assets[1]["asset_type"], AssetType.CRYPTO)
        self.assertEqual(assets[2]["asset_type"], AssetType.STEAM)
        self.assertEqual(assets[0]["symbol"], "NVDA")
        self.assertEqual(assets[1]["symbol"], "ETH")
        self.assertEqual(assets[2]["symbol"], HERO_STEAM_NAME)
        self.assertEqual(assets[2]["app_id"], 730)


class HeroMockupContextTests(TestCase):
    def setUp(self):
        cache.clear()

    @patch("apps.main.services.hero_mockup._build_hero_mockup_context")
    def test_build_hero_mockup_context_uses_cache(self, build_mock):
        payload = {"has_data": True, "assets": []}
        build_mock.return_value = payload

        first = build_hero_mockup_context()
        second = build_hero_mockup_context()

        self.assertEqual(first, payload)
        self.assertEqual(second, payload)
        build_mock.assert_called_once()

    @patch("apps.main.services.hero_mockup.InvestAPIClient")
    def test_build_hero_mockup_uses_one_unit_each(self, client_cls):
        client = MagicMock()
        client_cls.return_value.__enter__.return_value = client

        with patch(
            "apps.main.services.hero_mockup.get_crypto_quotes",
            return_value={"ethereum": MagicMock(price=Decimal("3000"))},
        ), patch(
            "apps.main.services.hero_mockup.get_price",
            side_effect=lambda asset_type, asset_name, app_id, client: {
                ("stock", "NVDA"): Decimal("900"),
                ("steam", HERO_STEAM_NAME): Decimal("45"),
            }.get((asset_type, asset_name)),
        ), patch(
            "apps.main.services.hero_mockup._fetch_market_result",
            return_value={
                "symbol": "NVDA",
                "price": "900.00",
                "change": "+1.00%",
                "pos": True,
            },
        ), patch(
            "apps.main.services.hero_mockup._build_portfolio_chart",
        ) as chart_mock:
            chart_mock.return_value = {
                "labels": ["May 1", "May 30"],
                "values": [3945.0, 4000.0],
                "points": [
                    {"t": "2026-05-01T00:00:00", "v": 3945.0},
                    {"t": "2026-05-30T00:00:00", "v": 4000.0},
                ],
            }
            ctx = build_hero_mockup_context(use_cache=False)

        self.assertTrue(ctx["has_data"])
        self.assertEqual(len(ctx["assets"]), 3)
        self.assertEqual(
            [a["asset_type"] for a in ctx["assets"]],
            [AssetType.STOCK, AssetType.CRYPTO, AssetType.STEAM],
        )
        self.assertEqual(ctx["total_value_dollars"], "3,945")
        self.assertEqual(ctx["chart_line_color"], "#4fc3f7")
        positions = chart_mock.call_args[0][0]
        self.assertEqual(len(positions), 3)
        for position in positions:
            self.assertEqual(position.quantity, HERO_QUANTITY)
