from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_not_required
from django.contrib.auth.views import LoginView
from django.shortcuts import get_object_or_404, redirect, render

from .cache import get_topic_leaderboard, get_topics, get_user_best
from .forms import AnswerForm, LoginForm, SignUpForm, StartAttemptForm
from .models import Attempt, Topic
from .services import start_attempt, submit_answer


@login_not_required
def signup(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("/")
    else:
        form = SignUpForm()
    return render(request, "exams/signup.html", {"form": form})


exam_login = login_not_required(
    LoginView.as_view(
        template_name="exams/login.html",
        authentication_form=LoginForm,
        redirect_authenticated_user=False,
    )
)


def topic_list(request):
    return render(request, "exams/topic_list.html", {"topics": get_topics()})


def result_list(request):
    history = Attempt.objects.filter(
        user=request.user,
        status=Attempt.Status.COMPLETED,
    ).order_by("-completed_at", "-id")
    return render(
        request,
        "exams/result_list.html",
        {"history": history, "best_results": get_user_best(request.user.id)},
    )


def leaderboard(request, topic_id):
    topic = get_object_or_404(Topic, pk=topic_id)
    return render(
        request,
        "exams/leaderboard.html",
        {"topic": topic, "rows": get_topic_leaderboard(topic_id)},
    )


def start_attempt_view(request):
    if request.method != "POST":
        return redirect("/")
    form = StartAttemptForm(request.POST)
    if not form.is_valid():
        for error in form.errors.values():
            messages.error(request, error[0])
        return redirect("/")
    try:
        attempt = start_attempt(form.cleaned_data["topic_id"], request.user)
    except ValueError as error:
        messages.error(request, str(error))
        return redirect("/")
    return redirect("attempt_question", pk=attempt.pk)


def attempt_question(request, pk):
    attempt = get_object_or_404(Attempt, pk=pk, user=request.user)
    if attempt.status == Attempt.Status.COMPLETED:
        return redirect("attempt_result", pk=attempt.pk)
    answer = (
        attempt.answers.filter(selected_option_key__isnull=True)
        .order_by("position")
        .first()
    )
    if answer is None:
        return redirect("attempt_result", pk=attempt.pk)
    return render(
        request,
        "exams/attempt_question.html",
        {
            "attempt": attempt,
            "answer": answer,
            "progress": f"Вопрос {answer.position} из {attempt.question_count}",
        },
    )


def attempt_answer(request, pk):
    attempt = get_object_or_404(Attempt, pk=pk, user=request.user)
    current = (
        attempt.answers.filter(selected_option_key__isnull=True)
        .order_by("position")
        .first()
    )
    option_key = request.POST.get("option_key", "")
    if current is not None:
        form = AnswerForm(request.POST, answer=current)
        if form.is_valid():
            option_key = form.cleaned_data["option_key"]

    message = submit_answer(attempt, option_key)
    attempt.refresh_from_db()
    if message:
        messages.error(request, message)

    if attempt.status == Attempt.Status.COMPLETED:
        return redirect("attempt_result", pk=attempt.pk)
    return redirect("attempt_question", pk=attempt.pk)


def attempt_result(request, pk):
    attempt = get_object_or_404(Attempt, pk=pk, user=request.user)
    if attempt.status != Attempt.Status.COMPLETED:
        return redirect("attempt_question", pk=attempt.pk)
    return render(
        request,
        "exams/attempt_result.html",
        {"attempt": attempt, "answers": attempt.answers.all()},
    )
