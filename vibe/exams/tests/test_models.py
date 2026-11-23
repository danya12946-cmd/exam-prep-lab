from django.db import IntegrityError, transaction
from django.test import TestCase

from exams.models import AnswerOption, Question, Topic
from exams.quiz import quiz_questions
from exams.tests.helpers import create_question


class QuestionTests(TestCase):
    def setUp(self):
        self.topic = Topic.objects.create(name="Python")
        self.question = create_question(self.topic, "Вопрос с одним верным ответом")

    def test_only_one_correct_option_is_allowed(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                AnswerOption.objects.create(
                    question=self.question,
                    text="Ещё один верный ответ",
                    is_correct=True,
                )

    def test_question_without_correct_option_is_excluded_from_quiz(self):
        invalid = Question.objects.create(topic=self.topic, text="Вопрос без ответа")
        AnswerOption.objects.create(question=invalid, text="Вариант", is_correct=False)

        available = quiz_questions(self.topic)

        self.assertIn(self.question, available)
        self.assertNotIn(invalid, available)

    def test_question_string_is_shortened(self):
        question = create_question(self.topic, "Очень длинный текст вопроса " * 5)
        self.assertLessEqual(len(str(question)), 80)
