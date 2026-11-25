from django.urls import path

from . import views

urlpatterns = [
    path("", views.topic_list, name="topic_list"),
    path("results/", views.result_list, name="results"),
    path(
        "topics/<int:topic_id>/leaderboard/",
        views.leaderboard,
        name="leaderboard",
    ),
    path("attempts/start/", views.start_attempt_view, name="attempt_start"),
    path(
        "attempts/<int:pk>/question/",
        views.attempt_question,
        name="attempt_question",
    ),
    path(
        "attempts/<int:pk>/answer/",
        views.attempt_answer,
        name="attempt_answer",
    ),
    path(
        "attempts/<int:pk>/result/",
        views.attempt_result,
        name="attempt_result",
    ),
]
