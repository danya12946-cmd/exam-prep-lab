from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TransactionTestCase

from exams.forms import AnswerOptionFormSet
from exams.models import AnswerOption, Attempt, Question, Topic
from exams.services import complete_attempt, start_attempt, submit_answer

User = get_user_model()


class AdminIntegrityTests(TransactionTestCase):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(username="admin-user", password="StrongPass123!")
        self.client.force_login(self.user)
        self.topic = Topic.objects.create(
            slug="integrity", title="Целостность", description="Проверка ограничений"
        )

    def create_question(self, option_count=4, correct_count=1):
        question = Question.objects.create(
            topic=self.topic,
            slug=f"integrity-q{Question.objects.count() + 1}",
            text="Исходный вопрос",
        )
        with transaction.atomic():
            for position in range(1, option_count + 1):
                AnswerOption.objects.create(
                    question=question,
                    position=position,
                    text=f"Вариант {position}",
                    is_correct=position <= correct_count,
                )
        return question

    def assert_commit_rejected(self, option_count, correct_count):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                question = Question.objects.create(
                    topic=self.topic,
                    slug=f"invalid-{option_count}-{correct_count}",
                    text="Некорректный вопрос",
                )
                for position in range(1, option_count + 1):
                    AnswerOption.objects.create(
                        question=question,
                        position=position,
                        text=f"Вариант {position}",
                        is_correct=position <= correct_count,
                    )

    def test_database_rejects_invalid_option_counts_and_correct_flags(self):
        self.assert_commit_rejected(1, 1)
        self.assert_commit_rejected(7, 1)
        self.assert_commit_rejected(4, 0)
        self.assert_commit_rejected(4, 2)

    def test_formset_rejects_invalid_options_with_russian_messages(self):
        question = self.create_question()
        data = {
            "options_set-TOTAL_FORMS": "1",
            "options_set-INITIAL_FORMS": "0",
            "options_set-MIN_NUM_FORMS": "0",
            "options_set-MAX_NUM_FORMS": "1000",
            "options_set-0-id": "",
            "options_set-0-question": str(question.pk),
            "options_set-0-position": "1",
            "options_set-0-text": "Единственный вариант",
            "options_set-0-is_correct": "on",
        }
        formset = AnswerOptionFormSet(data, instance=question, prefix="options_set")
        self.assertFalse(formset.is_valid())
        self.assertIn(
            "Вопрос должен иметь от 2 до 6 вариантов ответа",
            str(formset.non_form_errors()),
        )

    def test_completed_attempt_keeps_snapshots_after_content_changes(self):
        question = self.create_question()
        attempt = start_attempt(self.topic, self.user)
        answer = attempt.answers.get(source_question_id=question.pk)
        submit_answer(attempt, answer.correct_option_key)
        complete_attempt(attempt)

        page = self.client.get(f"/attempts/{attempt.pk}/result/")
        self.assertContains(page, "Исходный вопрос")
        self.assertContains(page, "100%")

        question.text = "Изменённый вопрос"
        question.save()
        correct = question.options.get(is_correct=True)
        other = question.options.exclude(pk=correct.pk).first()
        with transaction.atomic():
            correct.is_correct = False
            correct.save()
            other.is_correct = True
            other.save()
        self.topic.delete()

        answer.refresh_from_db()
        attempt.refresh_from_db()
        self.assertEqual(answer.question_text_snapshot, "Исходный вопрос")
        self.assertEqual(answer.correct_text_snapshot, "Вариант 1")
        self.assertEqual(attempt.status, Attempt.Status.COMPLETED)
        self.assertEqual(attempt.percent, 100)
        self.assertIsNone(attempt.topic)

        page = self.client.get(f"/attempts/{attempt.pk}/result/")
        self.assertContains(page, "Исходный вопрос")
        self.assertContains(page, "100%")
        self.assertNotContains(page, "Изменённый вопрос")
