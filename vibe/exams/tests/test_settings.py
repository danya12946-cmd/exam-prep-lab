from django.conf import settings
from django.test import SimpleTestCase


class CodespacesSettingsTests(SimpleTestCase):
    def test_codespaces_hosts_are_allowed(self):
        self.assertIn(".app.github.dev", settings.ALLOWED_HOSTS)

    def test_codespaces_origins_are_trusted_for_csrf(self):
        self.assertIn("https://*.app.github.dev", settings.CSRF_TRUSTED_ORIGINS)

    def test_https_proxy_header_is_enabled(self):
        self.assertEqual(
            settings.SECURE_PROXY_SSL_HEADER,
            ("HTTP_X_FORWARDED_PROTO", "https"),
        )
