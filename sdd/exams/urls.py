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
    path(
        "attempts/<int:pk>/question/",
        views.attempt_question,
        name="attempt_question",
    ),
]
