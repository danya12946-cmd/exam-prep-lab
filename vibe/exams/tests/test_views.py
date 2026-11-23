from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from exams.models import AttemptAnswer, Question, QuizAttempt, Topic
from exams.quiz import SESSION_KEY
from exams.tests.helpers import create_question

User = get_user_model()


class PublicPagesTests(TestCase):
    def setUp(self):
        self.topic = Topic.objects.create(name="Python")

    def test_home_and_topic_pages_open(self):
        self.assertEqual(self.client.get(reverse("home")).status_code, 200)
        self.assertEqual(self.client.get(reverse("topics")).status_code, 200)

    def test_registration_creates_user_and_logs_in(self):
        response = self.client.post(
            reverse("signup"),
            {
                "username": "student",
                "password1": "HardPass123!",
                "password2": "HardPass123!",
            },
        )

        self.assertRedirects(response, reverse("topics"))
        self.assertIn("_auth_user_id", self.client.session)
        self.assertTrue(User.objects.filter(username="student").exists())

    def test_login_with_valid_credentials(self):
        User.objects.create_user(username="student", password="HardPass123!")

        response = self.client.post(
            reverse("login"),
            {"username": "student", "password": "HardPass123!"},
        )

        self.assertRedirects(response, reverse("topics"))
        self.assertIn("_auth_user_id", self.client.session)


class QuizFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="student", password="HardPass123!")
        self.topic = Topic.objects.create(name="Python")
        self.questions = [
            create_question(self.topic, f"Вопрос {index}") for index in range(10)
        ]
        self.client.force_login(self.user)

    def start_quiz(self):
        response = self.client.post(reverse("quiz_start", args=[self.topic.pk]))
        self.assertRedirects(response, reverse("quiz"))
        return self.client.session[SESSION_KEY]

    def test_start_quiz_selects_ten_questions_from_topic(self):
        state = self.start_quiz()

        self.assertEqual(len(state["question_ids"]), 10)
        self.assertEqual(
            Question.objects.filter(
                id__in=state["question_ids"], topic=self.topic
            ).count(),
            10,
        )

    def test_quiz_requires_login(self):
        self.client.logout()

        start = self.client.post(reverse("quiz_start", args=[self.topic.pk]))
        results = self.client.get(reverse("my_results"))

        self.assertEqual(start.status_code, 302)
        self.assertTrue(start.url.startswith(reverse("login")))
        self.assertEqual(results.status_code, 302)
        self.assertTrue(results.url.startswith(reverse("login")))

    def test_answer_is_required(self):
        self.start_quiz()

        response = self.client.post(reverse("quiz"), {})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Выберите один из вариантов ответа.")

    def test_full_quiz_flow_saves_score_and_breakdown(self):
        state = self.start_quiz()
        wrong_question_text = None
        wrong_correct_answer = None

        for index, question_id in enumerate(state["question_ids"]):
            question = Question.objects.get(pk=question_id)
            correct = question.options.get(is_correct=True)
            if index % 2 == 0:
                selected = correct
            else:
                selected = question.options.exclude(is_correct=True).first()
                wrong_question_text = question.text
                wrong_correct_answer = correct.text

            response = self.client.post(reverse("quiz"), {"answer": selected.pk})
            if index < 9:
                self.assertRedirects(response, reverse("quiz"))

        attempt = QuizAttempt.objects.get(user=self.user)
        self.assertRedirects(response, reverse("result", args=[attempt.pk]))
        self.assertEqual(attempt.score, 5)
        self.assertEqual(attempt.total_questions, 10)
        self.assertEqual(attempt.answers.count(), 10)
        self.assertEqual(attempt.answers.filter(is_correct=False).count(), 5)

        result_page = self.client.get(reverse("result", args=[attempt.pk]))
        self.assertContains(result_page, "Правильных ответов: 5 из 10")
        self.assertContains(result_page, wrong_question_text)
        self.assertContains(result_page, wrong_correct_answer)

        results_page = self.client.get(reverse("my_results"))
        self.assertContains(results_page, reverse("result", args=[attempt.pk]))

    def test_result_page_is_private(self):
        attempt = QuizAttempt.objects.create(
            user=self.user,
            topic=self.topic,
            score=10,
            total_questions=10,
        )
        AttemptAnswer.objects.create(
            attempt=attempt,
            question_text="Вопрос",
            selected_text="Ответ",
            correct_text="Ответ",
            is_correct=True,
            order=1,
        )
        other_user = User.objects.create_user(
            username="other", password="HardPass123!"
        )
        self.client.force_login(other_user)

        response = self.client.get(reverse("result", args=[attempt.pk]))

        self.assertEqual(response.status_code, 404)

    def test_admin_allows_adding_questions_with_options(self):
        admin_user = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="HardPass123!",
        )
        self.client.force_login(admin_user)

        response = self.client.get("/admin/exams/question/add/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "is_correct")


class QuestionAdminValidationTests(TestCase):
    def setUp(self):
        self.topic = Topic.objects.create(name="Python")
        admin_user = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="HardPass123!",
        )
        self.client.force_login(admin_user)

    def save_question(self, options):
        data = {
            "topic": self.topic.pk,
            "text": "Вопрос из админки",
            "options-TOTAL_FORMS": len(options),
            "options-INITIAL_FORMS": 0,
            "options-MIN_NUM_FORMS": 2,
            "options-MAX_NUM_FORMS": 1000,
        }
        for index, (text, is_correct) in enumerate(options):
            data[f"options-{index}-text"] = text
            if is_correct:
                data[f"options-{index}-is_correct"] = "on"
        return self.client.post("/admin/exams/question/add/", data)

    def test_saving_question_requires_one_correct_option(self):
        response = self.save_question([("Вариант 1", False), ("Вариант 2", False)])

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Отметьте ровно один правильный ответ.")
        self.assertFalse(Question.objects.filter(text="Вопрос из админки").exists())

    def test_saving_question_requires_at_least_two_options(self):
        response = self.save_question([("Вариант 1", True)])

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "У вопроса должно быть минимум 2 варианта ответа.")
        self.assertFalse(Question.objects.filter(text="Вопрос из админки").exists())
