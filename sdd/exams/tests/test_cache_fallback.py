from unittest.mock import patch

from django.contrib.auth import get_user_model
from redis.exceptions import ConnectionError

from exams.models import Topic

from .helpers import CachedTestCase, load_demo_data

User = get_user_model()


class CacheFallbackTests(CachedTestCase):
    def setUp(self):
        super().setUp()
        load_demo_data()

    def test_pages_fall_back_to_database_when_cache_fails(self):
        user = User.objects.create_user(
            username="fallback-user", password="StrongPass123!"
        )
        self.client.force_login(user)

        with (
            patch("django.core.cache.cache.get", side_effect=ConnectionError),
            patch("django.core.cache.cache.set", side_effect=ConnectionError),
            self.assertLogs("exams.cache", level="WARNING") as logs,
        ):
            response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Алгебра")
        self.assertTrue(any("Не удалось прочитать кэш" in line for line in logs.output))
        self.assertTrue(any("Не удалось записать кэш" in line for line in logs.output))

    def test_failed_invalidation_does_not_break_database_write(self):
        with (
            patch("django.core.cache.cache.delete_many", side_effect=ConnectionError),
            self.assertLogs("exams.cache", level="WARNING") as logs,
        ):
            with self.captureOnCommitCallbacks(execute=True):
                Topic.objects.create(
                    slug="fallback-topic",
                    title="Тема при сбое кэша",
                    description="Описание",
                )

        self.assertTrue(Topic.objects.filter(slug="fallback-topic").exists())
        self.assertTrue(
            any("Не удалось удалить ключи кэша" in line for line in logs.output)
        )
