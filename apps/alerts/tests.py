from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.alerts.forms import (
    ASSET_NOT_FOUND_MSG,
    STEAM_DEFAULT_APP_ID,
    CreateAlertForm,
)
from apps.core.services.invest_api import InvestAPIError
from apps.alerts.models import Alert, AlertDirection
from apps.alerts.services.alerts_page import (
    _QuoteCacheKey,
    _alert_display_name,
    build_alerts_page_context,
    check_and_trigger_alerts,
    create_alert,
)
from apps.core.services.invest_api import PriceQuote
from apps.portfolio.types import AssetType

User = get_user_model()


def _quote(price: str, **kwargs) -> PriceQuote:
    return PriceQuote(
        asset_type=kwargs.get("asset_type", AssetType.STOCK),
        name=kwargs.get("name", "NVDA"),
        price=Decimal(price),
        currency="USD",
        symbol=kwargs.get("symbol"),
    )


class AlertTriggerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alertuser", password="pass")

    @patch("apps.alerts.services.alerts_page.get_quote")
    def test_check_and_trigger_alerts_fires_when_condition_met(self, mock_get_quote):
        alert = Alert.objects.create(
            user=self.user,
            asset_type=AssetType.STOCK,
            asset_name="NVDA",
            target_price=Decimal("100"),
            direction=AlertDirection.GT,
        )
        mock_get_quote.return_value = _quote("150")

        check_and_trigger_alerts(self.user)

        alert.refresh_from_db()
        self.assertFalse(alert.is_active)
        self.assertIsNotNone(alert.triggered_at)
        mock_get_quote.assert_called()

    @patch("apps.alerts.services.alerts_page.get_quote")
    def test_check_and_trigger_skips_when_price_unavailable(self, mock_get_quote):
        alert = Alert.objects.create(
            user=self.user,
            asset_type=AssetType.STOCK,
            asset_name="NVDA",
            target_price=Decimal("100"),
            direction=AlertDirection.GT,
        )
        mock_get_quote.return_value = None

        check_and_trigger_alerts(self.user)

        alert.refresh_from_db()
        self.assertTrue(alert.is_active)
        self.assertIsNone(alert.triggered_at)


class AlertDisplayNameTests(TestCase):
    def test_crypto_uses_quote_symbol_upper(self):
        alert = Alert(
            asset_type=AssetType.CRYPTO,
            asset_name="bitcoin",
        )
        quote = _quote(
            "1",
            asset_type=AssetType.CRYPTO,
            name="bitcoin",
            symbol="btc",
        )
        self.assertEqual(_alert_display_name(alert, quote), "BTC")


class CreateAlertFormTests(TestCase):
    @patch("apps.alerts.forms.get_quote")
    def test_steam_defaults_app_id(self, mock_get_quote):
        mock_get_quote.return_value = _quote("50")
        form = CreateAlertForm(
            {
                "asset_type": AssetType.STEAM,
                "asset_name": "AK-47 | Redline (Field-Tested)",
                "direction": AlertDirection.GT,
                "target_price": "50",
            },
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["app_id"], STEAM_DEFAULT_APP_ID)

    @patch("apps.alerts.forms.get_quote")
    def test_steam_uses_submitted_app_id(self, mock_get_quote):
        mock_get_quote.return_value = _quote("10")
        form = CreateAlertForm(
            {
                "asset_type": AssetType.STEAM,
                "asset_name": "Glove Case",
                "app_id": "570",
                "direction": AlertDirection.GT,
                "target_price": "10",
            },
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["app_id"], 570)

    @patch("apps.alerts.forms.get_quote")
    def test_rejects_unknown_asset(self, mock_get_quote):
        mock_get_quote.return_value = None
        form = CreateAlertForm(
            {
                "asset_type": AssetType.STOCK,
                "asset_name": "NOTAREALTICKER",
                "direction": AlertDirection.GT,
                "target_price": "100",
            },
        )
        self.assertFalse(form.is_valid())
        self.assertIn(ASSET_NOT_FOUND_MSG, form.errors["asset_name"])

    @patch("apps.alerts.forms.get_quote")
    def test_rejects_when_api_unavailable(self, mock_get_quote):
        mock_get_quote.side_effect = InvestAPIError("down")
        form = CreateAlertForm(
            {
                "asset_type": AssetType.STOCK,
                "asset_name": "NVDA",
                "direction": AlertDirection.GT,
                "target_price": "100",
            },
        )
        self.assertFalse(form.is_valid())
        self.assertIn("asset_name", form.errors)


class AlertsViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="viewer", password="pass")
        self.client = Client()
        self.client.login(username="viewer", password="pass")

    @patch("apps.alerts.services.alerts_page._fetch_quotes")
    @patch("apps.alerts.services.alerts_page.check_and_trigger_alerts")
    def test_alerts_page_renders_crypto_symbol(self, _mock_trigger, mock_quotes):
        Alert.objects.create(
            user=self.user,
            asset_type=AssetType.CRYPTO,
            asset_name="bitcoin",
            target_price=Decimal("50000"),
            direction=AlertDirection.GTE,
        )
        key = _QuoteCacheKey(AssetType.CRYPTO, "bitcoin", None)
        mock_quotes.return_value = {
            key: _quote("48000", asset_type=AssetType.CRYPTO, name="bitcoin", symbol="btc"),
        }

        response = self.client.get(reverse("alerts:alerts"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "BTC")
        self.assertContains(response, "48,000")

    @patch("apps.alerts.forms.get_quote")
    def test_create_alert_post(self, mock_get_quote):
        mock_get_quote.return_value = _quote("100")
        response = self.client.post(
            reverse("alerts:create"),
            {
                "asset_type": AssetType.STOCK,
                "asset_name": "AMD",
                "direction": AlertDirection.LT,
                "target_price": "200",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Alert.objects.filter(
                user=self.user,
                asset_name="AMD",
                target_price=Decimal("200"),
            ).exists(),
        )

    @patch("apps.alerts.forms.get_quote")
    def test_create_steam_alert_with_parentheses(self, mock_get_quote):
        mock_get_quote.return_value = _quote("50")
        response = self.client.post(
            reverse("alerts:create"),
            {
                "asset_type": AssetType.STEAM,
                "asset_name": "AK-47 | Redline (Field-Tested)",
                "direction": AlertDirection.GT,
                "target_price": "50",
            },
        )
        self.assertEqual(response.status_code, 302)
        alert = Alert.objects.get(user=self.user, asset_name="AK-47 | Redline (Field-Tested)")
        self.assertEqual(alert.app_id, STEAM_DEFAULT_APP_ID)

    @patch("apps.alerts.forms.get_quote")
    def test_create_alert_rejects_unknown_asset(self, mock_get_quote):
        mock_get_quote.return_value = None
        response = self.client.post(
            reverse("alerts:create"),
            {
                "asset_type": AssetType.STOCK,
                "asset_name": "FAKECO",
                "direction": AlertDirection.GT,
                "target_price": "100",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Alert.objects.filter(user=self.user).exists())

    def test_delete_alert_post(self):
        alert = create_alert(
            self.user,
            asset_type=AssetType.STOCK,
            asset_name="AAPL",
            app_id=None,
            direction=AlertDirection.GT,
            target_price=Decimal("300"),
        )
        response = self.client.post(reverse("alerts:delete", kwargs={"pk": alert.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Alert.objects.filter(pk=alert.pk).exists())

    @patch("apps.alerts.services.alerts_page._fetch_quotes")
    @patch("apps.alerts.services.alerts_page.check_and_trigger_alerts")
    def test_build_context_includes_detail_url(self, _mock_trigger, mock_quotes):
        Alert.objects.create(
            user=self.user,
            asset_type=AssetType.STOCK,
            asset_name="MSFT",
            target_price=Decimal("400"),
            direction=AlertDirection.GT,
        )
        mock_quotes.return_value = {
            _QuoteCacheKey(AssetType.STOCK, "MSFT", None): _quote("350"),
        }

        ctx = build_alerts_page_context(self.user)

        self.assertEqual(len(ctx["alerts"]), 1)
        self.assertIn("/stocks/", ctx["alerts"][0]["detail_url"])
        self.assertEqual(ctx["alerts"][0]["display_name"], "MSFT")

    @patch("apps.alerts.services.alerts_page._fetch_quotes")
    @patch("apps.alerts.services.alerts_page.check_and_trigger_alerts")
    def test_build_context_stats(self, _mock_trigger, mock_quotes):
        active = Alert.objects.create(
            user=self.user,
            asset_type=AssetType.STOCK,
            asset_name="MSFT",
            target_price=Decimal("400"),
            direction=AlertDirection.GT,
        )
        Alert.objects.create(
            user=self.user,
            asset_type=AssetType.STOCK,
            asset_name="MSFT",
            target_price=Decimal("500"),
            direction=AlertDirection.GT,
            is_active=False,
            triggered_at=timezone.now(),
        )
        mock_quotes.return_value = {
            _QuoteCacheKey(AssetType.STOCK, "MSFT", None): _quote("350"),
        }

        ctx = build_alerts_page_context(self.user)

        self.assertEqual(ctx["active_count"], 1)
        self.assertEqual(ctx["total_alerts"], 2)
        self.assertEqual(ctx["inactive_count"], 1)
        self.assertEqual(ctx["alerts"][0]["pk"], active.pk)
