from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings


def load_demo_data():
    call_command("load_demo_data", verbosity=0, stdout=StringIO())


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "exam-tests",
        }
    },
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
)
class CachedTestCase(TestCase):
    def setUp(self):
        super().setUp()
        from django.core.cache import cache

        cache.clear()
