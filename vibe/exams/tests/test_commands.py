from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from exams.models import Question, Topic


class LoadDemoDataTests(TestCase):
    def test_command_loads_topics_with_valid_questions(self):
        output = StringIO()
        call_command("load_demo_data", stdout=output)

        self.assertEqual(Topic.objects.count(), 3)
        for topic in Topic.objects.all():
            questions = Question.objects.filter(topic=topic)
            self.assertGreaterEqual(questions.count(), 10)
            for question in questions:
                options = list(question.options.all())
                self.assertTrue(3 <= len(options) <= 4)
                self.assertEqual(sum(option.is_correct for option in options), 1)

        self.assertIn("Демо-данные загружены", output.getvalue())

    def test_command_can_be_run_twice(self):
        call_command("load_demo_data", stdout=StringIO())
        topic_count = Topic.objects.count()
        question_count = Question.objects.count()
        option_count = sum(question.options.count() for question in Question.objects.all())

        call_command("load_demo_data", stdout=StringIO())

        self.assertEqual(Topic.objects.count(), topic_count)
        self.assertEqual(Question.objects.count(), question_count)
        self.assertEqual(
            sum(question.options.count() for question in Question.objects.all()),
            option_count,
        )
