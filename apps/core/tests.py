import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from django.core.cache import cache
from django.test import SimpleTestCase, override_settings

from apps.core.services.invest_api import (
    InvestAPIClient,
    InvestAPIError,
    get_price,
    period_change_pct,
)
from apps.core.services.ticker import format_change_delta
from apps.portfolio.types import AssetType


def _mock_aiohttp_response(*, status: int = 200, json_data: dict | None = None, text: str = ""):
    response = AsyncMock()
    response.status = status
    response.json = AsyncMock(return_value=json_data or {})
    response.text = AsyncMock(return_value=text)
    response.__aenter__ = AsyncMock(return_value=response)
    response.__aexit__ = AsyncMock(return_value=None)
    return response


class InvestAPIClientTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    @override_settings(INVEST_API_BASE_URL="https://api.example.com")
    def test_get_stock_parses_response(self):
        mock_response = _mock_aiohttp_response(
            json_data={
                "asset_type": "stock",
                "name": "NVDA",
                "price": 215.33,
                "currency": "USD",
                "source": "Yahoo Finance",
                "full_name": "NVIDIA Corporation",
            }
        )
        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.close = AsyncMock()

        client = InvestAPIClient(session=mock_session)

        quote = asyncio.run(client.get_stock("nvda"))

        self.assertEqual(quote.name, "NVDA")
        self.assertEqual(quote.price, Decimal("215.33"))
        mock_session.get.assert_called_once()
        call_args = mock_session.get.call_args
        self.assertEqual(call_args[0][0], "https://api.example.com/stock/NVDA")

    @override_settings(INVEST_API_BASE_URL="https://api.example.com")
    def test_uses_cache_on_second_call(self):
        mock_response = _mock_aiohttp_response(
            json_data={
                "asset_type": "crypto",
                "name": "solana",
                "price": 82.28,
                "currency": "USD",
            }
        )
        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.close = AsyncMock()

        client = InvestAPIClient(session=mock_session)

        async def run_twice():
            await client.get_crypto("solana")
            await client.get_crypto("solana")

        asyncio.run(run_twice())

        self.assertEqual(mock_session.get.call_count, 1)

    @override_settings(INVEST_API_BASE_URL="https://api.example.com")
    def test_get_price_returns_none_on_404(self):
        mock_response = _mock_aiohttp_response(status=404)
        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.close = AsyncMock()

        async def run():
            async with InvestAPIClient(session=mock_session) as client:
                return await get_price(AssetType.STOCK, "UNKNOWN", client=client)

        price = asyncio.run(run())
        self.assertIsNone(price)

    @override_settings(INVEST_API_BASE_URL="https://api.example.com")
    def test_steam_url_encodes_market_name(self):
        mock_response = _mock_aiohttp_response(
            json_data={
                "asset_type": "steam",
                "name": "Danger Zone Case",
                "price": 2.38,
                "currency": "USD",
                "app_id": 730,
            }
        )
        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.close = AsyncMock()

        asyncio.run(InvestAPIClient(session=mock_session).get_steam(730, "Danger Zone Case"))

        called_url = mock_session.get.call_args[0][0]
        self.assertIn("Danger%20Zone%20Case", called_url)

    @override_settings(INVEST_API_BASE_URL="https://api.example.com")
    def test_get_stock_history(self):
        mock_response = _mock_aiohttp_response(
            json_data={
                "asset_type": "stock",
                "name": "NVDA",
                "points": [
                    {"timestamp": "2026-05-18", "price": 100.0},
                    {"timestamp": "2026-05-22", "price": 110.0},
                ],
            }
        )
        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.close = AsyncMock()

        history = asyncio.run(
            InvestAPIClient(session=mock_session).get_stock_history("NVDA", days=7)
        )

        self.assertEqual(len(history.points), 2)
        self.assertEqual(period_change_pct(history.points), Decimal("10"))
        self.assertEqual(mock_session.get.call_args.kwargs.get("params"), {"days": 7})

    def test_format_change_delta(self):
        delta, positive = format_change_delta(Decimal("2.34"))
        self.assertTrue(positive)
        self.assertEqual(delta, "+2.34%")

        delta, positive = format_change_delta(Decimal("-0.96"))
        self.assertFalse(positive)
        self.assertEqual(delta, "0.96%")
        self.assertNotIn("-", delta)

    @override_settings(INVEST_API_BASE_URL="https://api.example.com")
    def test_raises_on_http_error(self):
        mock_response = _mock_aiohttp_response(status=500, text="Internal Server Error")
        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.close = AsyncMock()

        with self.assertRaises(InvestAPIError):
            asyncio.run(InvestAPIClient(session=mock_session).get_stock("NVDA"))
