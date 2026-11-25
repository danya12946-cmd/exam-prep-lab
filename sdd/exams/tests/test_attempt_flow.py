from django.contrib.auth import get_user_model

from exams.models import Attempt, Topic

from .helpers import CachedTestCase, create_question, load_demo_data

User = get_user_model()


class AttemptFlowTests(CachedTestCase):
    def setUp(self):
        super().setUp()
        load_demo_data()
        self.user = User.objects.create_user(username="student", password="StrongPass123!")
        self.client.force_login(self.user)
        self.topic = Topic.objects.get(slug="algebra")

    def start(self, topic):
        response = self.client.post("/attempts/start/", {"topic_id": topic.pk})
        self.assertEqual(response.status_code, 302)
        attempt = Attempt.objects.filter(user=self.user).order_by("-id").first()
        self.assertIsNotNone(attempt)
        return response, attempt

    def test_start_selects_ten_of_twelve_questions(self):
        _, attempt = self.start(self.topic)
        source_ids = set(attempt.answers.values_list("source_question_id", flat=True))
        topic_ids = set(self.topic.questions.values_list("id", flat=True))
        self.assertEqual(attempt.answers.count(), 10)
        self.assertEqual(attempt.question_count, 10)
        self.assertTrue(source_ids.issubset(topic_ids))

    def test_start_uses_all_questions_when_fewer_than_ten(self):
        topic = Topic.objects.create(
            slug="short", title="Короткая тема", description="Шесть вопросов"
        )
        for index in range(6):
            create_question(topic, f"short-q{index}", f"Вопрос {index}")
        _, attempt = self.start(topic)
        self.assertEqual(attempt.answers.count(), 6)
        page = self.client.get(f"/attempts/{attempt.pk}/question/")
        self.assertContains(page, "Вопрос 1 из 6")

    def test_progress_and_single_question_per_page(self):
        _, attempt = self.start(self.topic)
        page = self.client.get(f"/attempts/{attempt.pk}/question/")
        self.assertContains(page, "Вопрос 1 из 10")
        answer = attempt.answers.get(position=1)
        for option in answer.options_snapshot:
            self.assertContains(page, option["text"])
        self.assertNotContains(page, attempt.answers.get(position=2).question_text_snapshot)

        response = self.client.post(
            f"/attempts/{attempt.pk}/answer/",
            {"option_key": answer.correct_option_key},
        )
        self.assertEqual(response.status_code, 302)
        page = self.client.get(response.url)
        self.assertContains(page, "Вопрос 2 из 10")

    def test_repeated_post_does_not_change_answer(self):
        _, attempt = self.start(self.topic)
        answer = attempt.answers.get(position=1)
        key = answer.options_snapshot[0]["key"]
        url = f"/attempts/{attempt.pk}/answer/"
        self.client.post(url, {"option_key": key})
        answer.refresh_from_db()
        self.assertEqual(answer.selected_option_key, key)

        response = self.client.post(url, {"option_key": key})
        self.assertEqual(response.status_code, 302)
        page = self.client.get(response.url)
        self.assertContains(page, "Ответ уже сохранён")
        answer.refresh_from_db()
        self.assertEqual(answer.selected_option_key, key)
        attempt.refresh_from_db()
        self.assertEqual(attempt.status, Attempt.Status.IN_PROGRESS)
        self.assertEqual(attempt.correct_count, 0)

    def test_invalid_option_key_is_rejected(self):
        _, attempt = self.start(self.topic)
        response = self.client.post(
            f"/attempts/{attempt.pk}/answer/", {"option_key": "missing"}
        )
        self.assertEqual(response.status_code, 302)
        page = self.client.get(response.url)
        self.assertContains(page, "Выберите один из предложенных вариантов")
        self.assertIsNone(attempt.answers.get(position=1).selected_option_key)

    def test_result_counts_percent_and_review(self):
        _, attempt = self.start(self.topic)
        for position in range(1, 11):
            answer = attempt.answers.get(position=position)
            if position <= 7:
                key = answer.correct_option_key
            else:
                key = next(
                    option["key"]
                    for option in answer.options_snapshot
                    if option["key"] != answer.correct_option_key
                )
            response = self.client.post(
                f"/attempts/{attempt.pk}/answer/", {"option_key": key}
            )
            expected = (
                f"/attempts/{attempt.pk}/result/"
                if position == 10
                else f"/attempts/{attempt.pk}/question/"
            )
            self.assertEqual(response.url, expected)

        attempt.refresh_from_db()
        self.assertEqual(attempt.status, Attempt.Status.COMPLETED)
        self.assertEqual(attempt.correct_count, 7)
        self.assertEqual(attempt.percent, 70)

        page = self.client.get(f"/attempts/{attempt.pk}/result/")
        self.assertContains(page, "7 из 10")
        self.assertContains(page, "70%")
        self.assertContains(page, "Верно", count=7)
        self.assertContains(page, "Неверно", count=3)

    def test_empty_topic_and_missing_topic_are_rejected(self):
        empty = Topic.objects.create(
            slug="empty", title="Пустая тема", description="Без вопросов"
        )
        response = self.client.post("/attempts/start/", {"topic_id": empty.pk})
        self.assertEqual(response.url, "/")
        page = self.client.get("/")
        self.assertContains(page, "В теме нет вопросов")

        response = self.client.post("/attempts/start/", {"topic_id": 999999})
        self.assertEqual(response.url, "/")
        page = self.client.get("/")
        self.assertContains(page, "Тема не найдена")
        self.assertEqual(Attempt.objects.filter(user=self.user).count(), 0)

    def test_new_attempt_can_start_after_interrupted_one(self):
        self.start(self.topic)
        first = Attempt.objects.filter(user=self.user).order_by("id").first()
        answer = first.answers.get(position=1)
        self.client.post(
            f"/attempts/{first.pk}/answer/", {"option_key": answer.correct_option_key}
        )
        self.start(self.topic)
        self.assertEqual(
            Attempt.objects.filter(user=self.user, topic=self.topic).count(), 2
        )
        first.refresh_from_db()
        self.assertEqual(first.status, Attempt.Status.IN_PROGRESS)
