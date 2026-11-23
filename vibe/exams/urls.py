from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("topics/", views.topic_list, name="topics"),
    path("topics/<int:topic_id>/start/", views.start_quiz, name="quiz_start"),
    path("quiz/", views.quiz, name="quiz"),
    path("results/", views.my_results, name="my_results"),
    path("attempts/<int:attempt_id>/", views.result, name="result"),
    path("accounts/signup/", views.SignupView.as_view(), name="signup"),
    path(
        "accounts/login/",
        LoginView.as_view(
            template_name="registration/login.html",
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path("accounts/logout/", LogoutView.as_view(next_page="home"), name="logout"),
]
