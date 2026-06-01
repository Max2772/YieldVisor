from allauth.socialaccount.adapter import get_adapter
from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site
from django.test import TestCase, override_settings
from django.urls import Resolver404, resolve, reverse


@override_settings(
    SOCIALACCOUNT_PROVIDERS={
        "google": {
            "APP": {"client_id": "test-google-id", "secret": "test-google-secret"},
        },
        "github": {
            "APP": {"client_id": "test-github-id", "secret": "test-github-secret"},
        },
    },
)
class OAuthUrlsTests(TestCase):
    def test_google_login_url_resolves(self):
        url = reverse("google_login")
        self.assertEqual(url, "/accounts/google/login/")

    def test_github_login_url_resolves(self):
        url = reverse("github_login")
        self.assertEqual(url, "/accounts/github/login/")

    def test_login_page_renders_oauth_forms_when_configured(self):
        response = self.client.get(reverse("user:login"))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        google_pos = content.find('action="/accounts/google/login/"')
        github_pos = content.find('action="/accounts/github/login/"')
        self.assertGreater(google_pos, -1)
        self.assertGreater(github_pos, -1)
        self.assertLess(google_pos, github_pos, "Google button must appear before GitHub")

    def test_allauth_account_ui_is_not_exposed(self):
        for path in (
            "/accounts/login/",
            "/accounts/password/reset/",
            "/accounts/email/",
            "/accounts/3rdparty/",
        ):
            with self.assertRaises(Resolver404, msg=path):
                resolve(path)

    def test_oauth_signup_fallback_redirects_to_registration(self):
        response = self.client.get("/accounts/signup/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/registration/")

    def test_accounts_root_and_connections_are_not_public(self):
        for path in ("/accounts/", "/accounts/connections/"):
            with self.assertRaises(Resolver404, msg=path):
                resolve(path)

    def test_get_app_prefers_env_over_duplicate_admin_socialapp(self):
        site = Site.objects.get_current()
        SocialApp.objects.create(
            provider="google",
            name="google-admin-dup",
            client_id="admin-client-id",
            secret="admin-secret",
        ).sites.add(site)
        app = get_adapter().get_app(None, "google")
        self.assertIsNone(app.pk)
        self.assertEqual(app.client_id, "test-google-id")
