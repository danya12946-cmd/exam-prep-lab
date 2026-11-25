from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone
from io import StringIO

from exams.models import Attempt, Topic

from .helpers import CachedTestCase

User = get_user_model()


class LeaderboardTests(CachedTestCase):
    def setUp(self):
        super().setUp()
        call_command("load_demo_data", verbosity=0, stdout=StringIO())
        self.viewer = User.objects.create_user(username="viewer", password="StrongPass123!")
        self.client.force_login(self.viewer)
        self.topic = Topic.objects.get(slug="algebra")

    def make_user_attempt(self, username, percent, completed_at):
        user = User.objects.create_user(username=username, password="StrongPass123!")
        return Attempt.objects.create(
            user=user,
            topic=self.topic,
            topic_id_snapshot=self.topic.id,
            topic_title_snapshot=self.topic.title,
            status=Attempt.Status.COMPLETED,
            question_count=10,
            correct_count=round(percent / 10),
            percent=percent,
            completed_at=completed_at,
        )

    def test_leaderboard_limits_to_ten_and_sorts_by_percent(self):
        now = timezone.now()
        for index in range(12):
            self.make_user_attempt(f"user{index:02d}", 50 + index, now - timedelta(minutes=index))

        response = self.client.get(f"/topics/{self.topic.pk}/leaderboard/")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertEqual(content.count("user"), 10)
        self.assertNotIn("user00", content)
        self.assertIn("user11", content)
        self.assertTrue(content.index("user11") < content.index("user10"))
        self.assertGreaterEqual(content.count("<tr>"), 11)

    def test_best_attempt_per_user_is_used_once(self):
        now = timezone.now()
        user = User.objects.create_user(username="solo", password="StrongPass123!")
        for percent in (50, 80, 70):
            Attempt.objects.create(
                user=user,
                topic=self.topic,
                topic_id_snapshot=self.topic.id,
                topic_title_snapshot=self.topic.title,
                status=Attempt.Status.COMPLETED,
                question_count=10,
                correct_count=round(percent / 10),
                percent=percent,
                completed_at=now - timedelta(minutes=10 - percent),
            )
        response = self.client.get(f"/topics/{self.topic.pk}/leaderboard/")
        self.assertContains(response, "solo")
        self.assertContains(response, "80%")
        self.assertNotContains(response, "50%")
        self.assertNotContains(response, "70%")

    def test_tie_break_uses_earliest_best_attempt_then_username(self):
        now = timezone.now()
        self.make_user_attempt("zulu", 90, now - timedelta(minutes=2))
        alpha = self.make_user_attempt("alpha", 90, now - timedelta(minutes=5))
        Attempt.objects.create(
            user=alpha.user,
            topic=self.topic,
            topic_id_snapshot=self.topic.id,
            topic_title_snapshot=self.topic.title,
            status=Attempt.Status.COMPLETED,
            question_count=10,
            correct_count=9,
            percent=90,
            completed_at=now - timedelta(minutes=1),
        )
        self.make_user_attempt("middle", 90, now - timedelta(minutes=5))

        response = self.client.get(f"/topics/{self.topic.pk}/leaderboard/")
        content = response.content.decode()
        self.assertTrue(content.index("middle") < content.index("alpha"))
        self.assertTrue(content.index("alpha") < content.index("zulu"))

    def test_empty_and_missing_topic(self):
        response = self.client.get(f"/topics/{self.topic.pk}/leaderboard/")
        self.assertContains(response, "Результатов пока нет")

        missing = Topic.objects.order_by("-id").first().id + 100
        response = self.client.get(f"/topics/{missing}/leaderboard/")
        self.assertEqual(response.status_code, 404)

    def test_in_progress_attempt_is_excluded_and_new_attempt_allowed(self):
        interrupted = Attempt.objects.create(
            user=self.viewer,
            topic=self.topic,
            topic_id_snapshot=self.topic.id,
            topic_title_snapshot=self.topic.title,
            status=Attempt.Status.IN_PROGRESS,
            question_count=10,
            correct_count=0,
            percent=0,
        )
        response = self.client.get(f"/topics/{self.topic.pk}/leaderboard/")
        self.assertContains(response, "Результатов пока нет")

        response = self.client.post("/attempts/start/", {"topic_id": self.topic.pk})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            Attempt.objects.filter(user=self.viewer, topic=self.topic).count(), 2
        )
        interrupted.refresh_from_db()
        self.assertEqual(interrupted.status, Attempt.Status.IN_PROGRESS)
