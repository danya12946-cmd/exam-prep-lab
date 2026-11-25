from datetime import timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone

from exams.models import Attempt, Topic

from .helpers import CachedTestCase

User = get_user_model()


class ResultsTests(CachedTestCase):
    def setUp(self):
        super().setUp()
        call_command("load_demo_data", verbosity=0, stdout=StringIO())
        self.user = User.objects.create_user(username="viewer", password="StrongPass123!")
        self.other = User.objects.create_user(username="another", password="StrongPass123!")
        self.client.force_login(self.user)
        self.algebra = Topic.objects.get(slug="algebra")
        self.geometry = Topic.objects.get(slug="geometry")
        self.programming = Topic.objects.get(slug="programming")

    def make_attempt(self, user, topic, percent, completed_at=None, status=Attempt.Status.COMPLETED):
        attempt = Attempt.objects.create(
            user=user,
            topic=topic,
            topic_id_snapshot=topic.id,
            topic_title_snapshot=topic.title,
            status=status,
            question_count=10,
            correct_count=round(percent / 10),
            percent=percent,
            completed_at=completed_at,
        )
        return attempt

    def test_history_is_newest_first_and_best_is_max_percent(self):
        now = timezone.now()
        oldest = self.make_attempt(self.user, self.programming, 60, now - timedelta(days=2))
        middle = self.make_attempt(self.user, self.geometry, 80, now - timedelta(days=1))
        newest = self.make_attempt(self.user, self.algebra, 90, now)

        response = self.client.get("/results/")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertTrue(content.index(newest.topic_title_snapshot) < content.index(middle.topic_title_snapshot))
        self.assertTrue(content.index(middle.topic_title_snapshot) < content.index(oldest.topic_title_snapshot))
        self.assertContains(response, "90%")
        self.assertContains(response, "80%")

        from exams.cache import get_user_best

        best = get_user_best(self.user.id)
        self.assertEqual([row["best_percent"] for row in best], [90, 80, 60])

    def test_foreign_attempt_returns_404(self):
        attempt = self.make_attempt(self.other, self.algebra, 100, timezone.now())
        response = self.client.get(f"/attempts/{attempt.pk}/result/")
        self.assertEqual(response.status_code, 404)

    def test_own_history_links_to_result(self):
        attempt = self.make_attempt(self.user, self.algebra, 70, timezone.now())
        response = self.client.get("/results/")
        self.assertContains(response, f"/attempts/{attempt.pk}/result/")

    def test_in_progress_attempt_is_excluded_and_new_attempt_is_allowed(self):
        interrupted = self.make_attempt(
            self.user, self.algebra, 0, None, status=Attempt.Status.IN_PROGRESS
        )
        response = self.client.get("/results/")
        self.assertNotContains(response, f"/attempts/{interrupted.pk}/result/")
        from exams.cache import get_user_best

        self.assertEqual(get_user_best(self.user.id), [])

        response = self.client.post("/attempts/start/", {"topic_id": self.algebra.pk})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            Attempt.objects.filter(user=self.user, topic=self.algebra).count(), 2
        )
