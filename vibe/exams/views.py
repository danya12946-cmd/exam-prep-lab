from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView

from .forms import SignUpForm
from .models import AttemptAnswer, Question, QuizAttempt, Topic
from .quiz import SESSION_KEY, correct_option, random_questions


def topics_with_counts():
    return Topic.objects.annotate(
        question_count=Count(
            "questions",
            filter=Q(questions__options__is_correct=True),
            distinct=True,
        )
    ).order_by("name")


class SignupView(CreateView):
    form_class = SignUpForm
    template_name = "registration/signup.html"
    success_url = reverse_lazy("topics")

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        messages.success(self.request, "Регистрация выполнена. Можно проходить тесты.")
        return response


def home(request):
    return render(
        request,
        "exams/home.html",
        {
            "topics": topics_with_counts()[:6],
            "required_count": settings.QUIZ_QUESTION_COUNT,
        },
    )


def topic_list(request):
    return render(
        request,
        "exams/topics.html",
        {
            "topics": topics_with_counts(),
            "required_count": settings.QUIZ_QUESTION_COUNT,
        },
    )


@login_required
@require_POST
def start_quiz(request, topic_id):
    topic = get_object_or_404(Topic, pk=topic_id)
    questions = random_questions(topic)
    if len(questions) < settings.QUIZ_QUESTION_COUNT:
        messages.error(
            request,
            f"В теме «{topic.name}» недостаточно вопросов "
            f"(нужно минимум {settings.QUIZ_QUESTION_COUNT}).",
        )
        return redirect("topics")

    request.session[SESSION_KEY] = {
        "topic_id": topic.id,
        "topic_name": topic.name,
        "question_ids": [question.id for question in questions],
        "answers": {},
    }
    return redirect("quiz")


def parse_option_id(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def save_attempt(user, state):
    question_ids = list(state["question_ids"])
    answers = state["answers"]
    topic = Topic.objects.get(pk=state["topic_id"])
    questions = {
        question.id: question
        for question in Question.objects.filter(id__in=question_ids).prefetch_related(
            "options"
        )
    }

    with transaction.atomic():
        attempt = QuizAttempt.objects.create(
            user=user,
            topic=topic,
            score=0,
            total_questions=len(question_ids),
        )
        records = []
        score = 0

        for order, question_id in enumerate(question_ids, start=1):
            question = questions.get(question_id)
            selected = None
            correct = None
            if question is not None:
                selected_id = answers.get(str(question_id))
                selected = next(
                    (option for option in question.options.all() if option.id == selected_id),
                    None,
                )
                correct = correct_option(question)

            is_correct = bool(
                selected is not None
                and correct is not None
                and selected.is_correct
                and selected.id == correct.id
            )
            records.append(
                AttemptAnswer(
                    attempt=attempt,
                    question=question,
                    question_text=question.text if question else "Вопрос больше не доступен",
                    selected_text=selected.text if selected else "Ответ не выбран",
                    correct_text=correct.text if correct else "Правильный ответ недоступен",
                    is_correct=is_correct,
                    order=order,
                )
            )
            if is_correct:
                score += 1

        AttemptAnswer.objects.bulk_create(records)
        attempt.score = score
        attempt.save(update_fields=["score"])

    return attempt


@login_required
def quiz(request):
    state = request.session.get(SESSION_KEY)
    if not state:
        messages.info(request, "Сначала выберите тему для теста.")
        return redirect("topics")

    question_ids = state.get("question_ids", [])
    answers = state.get("answers", {})
    if not question_ids or len(answers) >= len(question_ids):
        request.session.pop(SESSION_KEY, None)
        messages.info(request, "Тест уже завершён. Выберите новую тему.")
        return redirect("topics")

    question_id = question_ids[len(answers)]
    question = (
        Question.objects.filter(pk=question_id, topic_id=state.get("topic_id"))
        .prefetch_related("options")
        .first()
    )
    if question is None:
        request.session.pop(SESSION_KEY, None)
        messages.error(request, "Вопрос больше не доступен. Начните тест заново.")
        return redirect("topics")

    if request.method == "POST":
        option_id = parse_option_id(request.POST.get("answer"))
        selected = next(
            (option for option in question.options.all() if option.id == option_id),
            None,
        )
        if selected is None:
            messages.error(request, "Выберите один из вариантов ответа.")
        else:
            answers[str(question_id)] = selected.id
            state["answers"] = answers
            request.session[SESSION_KEY] = state

            if len(answers) == len(question_ids):
                if not Topic.objects.filter(pk=state["topic_id"]).exists():
                    request.session.pop(SESSION_KEY, None)
                    messages.error(request, "Тема больше не доступна.")
                    return redirect("topics")
                attempt = save_attempt(request.user, state)
                request.session.pop(SESSION_KEY, None)
                messages.success(request, "Тест завершён. Результат сохранён.")
                return redirect("result", attempt_id=attempt.pk)

            return redirect("quiz")

    return render(
        request,
        "exams/quiz.html",
        {
            "question": question,
            "options": question.options.all(),
            "topic_name": state.get("topic_name", ""),
            "current": len(answers) + 1,
            "total": len(question_ids),
        },
    )


@login_required
def result(request, attempt_id):
    attempt = get_object_or_404(
        QuizAttempt.objects.select_related("topic").prefetch_related("answers"),
        pk=attempt_id,
        user=request.user,
    )
    return render(request, "exams/result.html", {"attempt": attempt})


@login_required
def my_results(request):
    attempts = request.user.quiz_attempts.select_related("topic").all()
    return render(request, "exams/results.html", {"attempts": attempts})
