from django.conf import settings
from django.db.models import Count, Q

from .models import Question

SESSION_KEY = "exam_quiz"


def quiz_questions(topic):
    return (
        Question.objects.filter(topic=topic)
        .annotate(correct_count=Count("options", filter=Q(options__is_correct=True)))
        .filter(correct_count=1)
    )


def random_questions(topic):
    return list(quiz_questions(topic).order_by("?")[: settings.QUIZ_QUESTION_COUNT])


def correct_option(question):
    return next((option for option in question.options.all() if option.is_correct), None)
