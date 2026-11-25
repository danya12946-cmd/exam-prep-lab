from django.contrib.auth import login
from django.contrib.auth.decorators import login_not_required
from django.contrib.auth.views import LoginView
from django.http import HttpResponse
from django.shortcuts import redirect, render

from .cache import get_topics
from .forms import LoginForm, SignUpForm


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
    return HttpResponse("")


def leaderboard(request, topic_id):
    return HttpResponse("")


def attempt_question(request, pk):
    return HttpResponse("")
