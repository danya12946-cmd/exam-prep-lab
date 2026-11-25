from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings

from exams.models import AnswerOption, Question


def load_demo_data():
    call_command("load_demo_data", verbosity=0, stdout=StringIO())


def create_question(topic, slug, text, options=("Верно", "Неверно 1", "Неверно 2")):
    question = Question.objects.create(topic=topic, slug=slug, text=text)
    for position, option_text in enumerate(options, 1):
        AnswerOption.objects.create(
            question=question,
            position=position,
            text=option_text,
            is_correct=position == 1,
        )
    return question


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
