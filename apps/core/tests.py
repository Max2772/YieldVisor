from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import RequestFactory, SimpleTestCase, override_settings

from apps.core.services.asset_detail import build_asset_detail_context
from apps.core.services.asset_logos import (
    _cache_key,
    _parse_steam_logo_from_html,
    crypto_logo_url,
    steam_logo_url,
    stock_logo_url,
)
from apps.stocks.views import StockView
from apps.core.services.invest_api import (
    InvestAPIClient,
    InvestAPIError,
    get_price,
    period_change_pct,
)
from apps.core.services.ticker import format_change_delta
from apps.portfolio.types import AssetType


def _mock_httpx_response(*, status_code: int = 200, json_data: dict | None = None, text: str = ""):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data or {}
    response.text = text
    return response


class InvestAPIClientTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    @override_settings(INVEST_API_BASE_URL="https://api.example.com")
    def test_get_stock_parses_response(self):
        mock_response = _mock_httpx_response(
            json_data={
                "asset_type": "stock",
                "name": "NVDA",
                "price": 215.33,
                "currency": "USD",
                "source": "Yahoo Finance",
                "full_name": "NVIDIA Corporation",
            }
        )
        mock_client = MagicMock()
        mock_client.get.return_value = mock_response

        client = InvestAPIClient(client=mock_client)
        quote = client.get_stock("nvda")

        self.assertEqual(quote.name, "NVDA")
        self.assertEqual(quote.price, Decimal("215.33"))
        mock_client.get.assert_called_once()
        call_args = mock_client.get.call_args
        self.assertEqual(call_args[0][0], "https://api.example.com/stock/NVDA")

    @override_settings(INVEST_API_BASE_URL="https://api.example.com")
    def test_uses_cache_on_second_call(self):
        mock_response = _mock_httpx_response(
            json_data={
                "asset_type": "crypto",
                "name": "solana",
                "price": 82.28,
                "currency": "USD",
            }
        )
        mock_client = MagicMock()
        mock_client.get.return_value = mock_response

        client = InvestAPIClient(client=mock_client)
        client.get_crypto("solana")
        client.get_crypto("solana")

        self.assertEqual(mock_client.get.call_count, 1)

    @override_settings(INVEST_API_BASE_URL="https://api.example.com")
    def test_get_price_returns_none_on_404(self):
        mock_response = _mock_httpx_response(status_code=404)
        mock_client = MagicMock()
        mock_client.get.return_value = mock_response

        with InvestAPIClient(client=mock_client) as client:
            price = get_price(AssetType.STOCK, "UNKNOWN", client=client)

        self.assertIsNone(price)

    @override_settings(INVEST_API_BASE_URL="https://api.example.com")
    def test_steam_url_encodes_market_name(self):
        mock_response = _mock_httpx_response(
            json_data={
                "asset_type": "steam",
                "name": "Danger Zone Case",
                "price": 2.38,
                "currency": "USD",
                "app_id": 730,
            }
        )
        mock_client = MagicMock()
        mock_client.get.return_value = mock_response

        InvestAPIClient(client=mock_client).get_steam(730, "Danger Zone Case")

        called_url = mock_client.get.call_args[0][0]
        self.assertIn("Danger%20Zone%20Case", called_url)

    @override_settings(INVEST_API_BASE_URL="https://api.example.com")
    def test_get_stock_history(self):
        mock_response = _mock_httpx_response(
            json_data={
                "asset_type": "stock",
                "name": "NVDA",
                "points": [
                    {"timestamp": "2026-05-18", "price": 100.0},
                    {"timestamp": "2026-05-22", "price": 110.0},
                ],
            }
        )
        mock_client = MagicMock()
        mock_client.get.return_value = mock_response

        history = InvestAPIClient(client=mock_client).get_stock_history("NVDA", days=7)

        self.assertEqual(len(history.points), 2)
        self.assertEqual(period_change_pct(history.points), Decimal("10"))
        self.assertEqual(mock_client.get.call_args.kwargs.get("params"), {"days": 7})

    def test_format_change_delta(self):
        delta, positive = format_change_delta(Decimal("2.34"))
        self.assertTrue(positive)
        self.assertEqual(delta, "+2.34%")

        delta, positive = format_change_delta(Decimal("-0.96"))
        self.assertFalse(positive)
        self.assertEqual(delta, "0.96%")
        self.assertNotIn("-", delta)

    @override_settings(INVEST_API_BASE_URL="https://api.example.com", TICKER_CHANGE_DAYS=7)
    def test_build_asset_detail_context(self):
        def fake_quote(*args, **kwargs):
            from apps.core.services.invest_api import _parse_quote

            return _parse_quote(
                {
                    "asset_type": "stock",
                    "name": "AMD",
                    "price": 467.51,
                    "currency": "USD",
                    "full_name": "Advanced Micro Devices, Inc.",
                }
            )

        def fake_history(*args, **kwargs):
            from apps.core.services.invest_api import _parse_history

            return _parse_history(
                {
                    "asset_type": "stock",
                    "name": "AMD",
                    "points": [
                        {"timestamp": "2026-05-18", "price": 420.99},
                        {"timestamp": "2026-05-22", "price": 467.51},
                    ],
                }
            )

        with patch(
            "apps.core.services.asset_detail.get_quote",
            side_effect=fake_quote,
        ), patch(
            "apps.core.services.asset_detail.get_history",
            side_effect=fake_history,
        ):
            ctx = build_asset_detail_context(
                AssetType.STOCK,
                "AMD",
                display_symbol="AMD",
                days=7,
            )

        self.assertIsNotNone(ctx)
        self.assertEqual(ctx["asset"]["symbol"], "AMD")
        self.assertIn("logo_url", ctx["asset"])
        self.assertTrue(ctx["asset"]["logo_url"])
        self.assertEqual(len(ctx["chart"]["prices"]), 2)
        self.assertTrue(ctx["asset"]["change_delta"])
        self.assertEqual(ctx["asset"]["market_symbol"], "AMD")

    @override_settings(INVEST_API_BASE_URL="https://api.example.com", TICKER_CHANGE_DAYS=7)
    def test_build_asset_detail_context_crypto_symbol(self):
        def fake_quote(*args, **kwargs):
            from apps.core.services.invest_api import _parse_quote

            return _parse_quote(
                {
                    "asset_type": "crypto",
                    "name": "bitcoin",
                    "price": 62000,
                    "currency": "USD",
                    "full_name": "Bitcoin",
                }
            )

        with patch(
            "apps.core.services.asset_detail.get_quote",
            side_effect=fake_quote,
        ), patch(
            "apps.core.services.asset_detail.get_history",
            return_value=None,
        ):
            ctx = build_asset_detail_context(
                AssetType.CRYPTO,
                "bitcoin",
                display_symbol="BITCOIN",
                days=7,
            )

        self.assertIsNotNone(ctx)
        self.assertEqual(ctx["asset"]["market_symbol"], "BTC")
        self.assertEqual(ctx["asset"]["hero_title"], "BITCOIN")
        self.assertEqual(ctx["asset"]["hero_subtitle"], "BTC")

    def test_render_asset_not_found(self):
        from django.contrib.auth.models import AnonymousUser

        request = RequestFactory().get("/stocks/FAKE/")
        request.user = AnonymousUser()
        view = StockView()
        response = view._render_asset_not_found(
            request,
            {"display_symbol": "FAKE"},
        )
        self.assertEqual(response.status_code, 404)
        self.assertIn(b"Asset not found", response.content)

    @override_settings(INVEST_API_BASE_URL="https://api.example.com")
    def test_raises_on_http_error(self):
        mock_response = _mock_httpx_response(status_code=500, text="Internal Server Error")
        mock_client = MagicMock()
        mock_client.get.return_value = mock_response

        with self.assertRaises(InvestAPIError):
            InvestAPIClient(client=mock_client).get_stock("NVDA")


class AssetLogoTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    def test_steam_cache_key_is_memcached_safe(self):
        key = _cache_key("steam", "730", "AK-47 | Redline (Field-Tested)")
        self.assertNotIn(" ", key)
        self.assertNotIn("|", key)
        self.assertTrue(key.startswith("asset_logo.steam.730."))

    def test_stock_logo_url_is_cached(self):
        url = stock_logo_url("tsla")
        self.assertIn("TSLA", url)
        self.assertEqual(url, stock_logo_url("TSLA"))

    def test_crypto_logo_url_uses_catalog_symbol(self):
        url = crypto_logo_url("bitcoin")
        self.assertIn("/btc.svg", url)
        self.assertEqual(url, crypto_logo_url("bitcoin"))

    def test_parse_steam_logo_from_html(self):
        html = (
            '<img src="https://community.steamstatic.com/economy/image/'
            'i0CoZ81Ui0m-9KwlBY1L_18myuGuq1wfhWSaZgMttyVfPaERSR0Wqmu7LAocGJKz2lu_XsnXwtmkJjSU91dh8bj35VTqVBP4io_frHcVuPaoafU1JqiVWWSVkux15OQ8Giiylk0k5mvTnIqpd3PCaQIhWMYkE_lK7EcNeCKW-w">'
        )
        logo = _parse_steam_logo_from_html(html)
        self.assertTrue(logo.startswith("https://community.steamstatic.com/economy/image/"))

    @patch("apps.core.services.asset_logos._fetch_steam_logo_from_market")
    def test_steam_logo_url_caches_result(self, fetch_mock):
        fetch_mock.return_value = (
            "https://community.steamstatic.com/economy/image/example"
        )
        url = steam_logo_url(730, "Glove Case")
        self.assertEqual(url, fetch_mock.return_value)
        fetch_mock.assert_called_once()
        self.assertEqual(steam_logo_url(730, "Glove Case"), url)
        fetch_mock.assert_called_once()
