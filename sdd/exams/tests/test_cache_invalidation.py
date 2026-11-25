from django.contrib.auth import get_user_model
from django.db import transaction
from exams.cache import (
    TOPICS_LIST_KEY,
    get_topic_leaderboard,
    get_topics,
    get_user_best,
    invalidate_direct_write,
)
from exams.models import Topic
from exams.services import start_attempt, submit_answer

from .helpers import CachedTestCase, load_demo_data

User = get_user_model()


class CacheInvalidationTests(CachedTestCase):
    def setUp(self):
        super().setUp()
        load_demo_data()

    def test_topics_list_is_cached_and_invalidated_after_commit(self):
        with self.assertNumQueries(1):
            first = get_topics()
        with self.assertNumQueries(0):
            get_topics()
        self.assertEqual(len(first), 3)

        with self.captureOnCommitCallbacks(execute=True):
            Topic.objects.create(
                slug="new-topic", title="Новая тема", description="Описание"
            )

        with self.assertNumQueries(1):
            updated = get_topics()
        self.assertIn("Новая тема", [row["title"] for row in updated])

    def test_rollback_does_not_invalidate_cache(self):
        get_topics()
        with self.assertRaises(RuntimeError):
            with self.captureOnCommitCallbacks(execute=True):
                with transaction.atomic():
                    Topic.objects.create(
                        slug="rolled-back", title="Отменённая тема", description="Описание"
                    )
                    raise RuntimeError("rollback")

        with self.assertNumQueries(0):
            cached = get_topics()
        self.assertNotIn("Отменённая тема", [row["title"] for row in cached])

    def test_result_caches_are_invalidated_after_attempt_completion(self):
        user = User.objects.create_user(username="cache-user", password="StrongPass123!")
        topic = Topic.objects.get(slug="algebra")
        attempt = start_attempt(topic, user)

        self.assertEqual(get_user_best(user.id), [])
        self.assertEqual(get_topic_leaderboard(topic.id), [])
        with self.assertNumQueries(0):
            get_user_best(user.id)

        answers = list(attempt.answers.order_by("position"))
        with self.captureOnCommitCallbacks(execute=True):
            for answer in answers:
                self.assertIsNone(
                    submit_answer(attempt, answer.correct_option_key)
                )

        with self.assertNumQueries(2):
            best = get_user_best(user.id)
        self.assertEqual(best[0]["best_percent"], 100)
        with self.assertNumQueries(3):
            leaderboard = get_topic_leaderboard(topic.id)
        self.assertEqual(leaderboard[0]["username"], user.username)

    def test_direct_write_helper_invalidates_cache_after_update(self):
        topic = Topic.objects.get(slug="algebra")
        get_topics()

        with self.captureOnCommitCallbacks(execute=True):
            with transaction.atomic():
                Topic.objects.filter(pk=topic.pk).update(title="Прямое обновление")
                invalidate_direct_write([TOPICS_LIST_KEY])

        with self.assertNumQueries(1):
            updated = get_topics()
        self.assertIn("Прямое обновление", [row["title"] for row in updated])
