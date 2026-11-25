from django.conf import settings
from django.db import models
from django.db.models import F, Q


class Topic(models.Model):
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.title


class Question(models.Model):
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="questions")
    slug = models.SlugField()
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["topic", "slug"],
                name="unique_question_slug_per_topic",
            )
        ]
        ordering = ["id"]

    def __str__(self):
        return self.text[:80]


class AnswerOption(models.Model):
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name="options"
    )
    position = models.PositiveSmallIntegerField()
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["question", "position"],
                name="unique_option_position_per_question",
            ),
            models.CheckConstraint(
                condition=Q(position__gte=1) & Q(position__lte=6),
                name="answer_option_position_between_1_and_6",
            ),
        ]
        ordering = ["position"]

    def __str__(self):
        return self.text


class Attempt(models.Model):
    class Status(models.TextChoices):
        IN_PROGRESS = "IN_PROGRESS", "В процессе"
        COMPLETED = "COMPLETED", "Завершена"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="attempts"
    )
    topic = models.ForeignKey(
        Topic,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attempts",
    )
    topic_id_snapshot = models.PositiveIntegerField()
    topic_title_snapshot = models.CharField(max_length=200)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.IN_PROGRESS,
    )
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    question_count = models.PositiveSmallIntegerField(default=0)
    correct_count = models.PositiveSmallIntegerField(default=0)
    percent = models.PositiveSmallIntegerField(default=0)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(question_count__gte=1) & Q(question_count__lte=10),
                name="attempt_question_count_between_1_and_10",
            ),
            models.CheckConstraint(
                condition=Q(correct_count__gte=0)
                & Q(correct_count__lte=F("question_count")),
                name="attempt_correct_count_bounded",
            ),
            models.CheckConstraint(
                condition=Q(percent__gte=0) & Q(percent__lte=100),
                name="attempt_percent_between_0_and_100",
            ),
            models.CheckConstraint(
                condition=Q(
                    status="COMPLETED", completed_at__isnull=False
                )
                | Q(status="IN_PROGRESS", completed_at__isnull=True),
                name="attempt_status_matches_completed_at",
            ),
        ]
        indexes = [
            models.Index(
                fields=["user", "status", "-started_at"],
                name="attempt_user_status_started",
            ),
            models.Index(
                fields=["topic", "status", "-percent", "completed_at"],
                name="attempt_topic_status_percent",
            ),
        ]
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.topic_title_snapshot} — {self.user}"


class AttemptAnswer(models.Model):
    attempt = models.ForeignKey(
        Attempt, on_delete=models.CASCADE, related_name="answers"
    )
    position = models.PositiveSmallIntegerField()
    source_question_id = models.PositiveIntegerField()
    question_text_snapshot = models.TextField()
    options_snapshot = models.JSONField(default=list)
    selected_option_key = models.CharField(max_length=16, null=True, blank=True)
    selected_text_snapshot = models.TextField(blank=True)
    correct_option_key = models.CharField(max_length=16, blank=True)
    correct_text_snapshot = models.TextField(blank=True)
    is_correct = models.BooleanField(null=True, blank=True)
    answered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["attempt", "position"],
                name="unique_answer_position_per_attempt",
            ),
            models.UniqueConstraint(
                fields=["attempt", "source_question_id"],
                name="unique_source_question_per_attempt",
            ),
            models.CheckConstraint(
                condition=Q(position__gte=1) & Q(position__lte=10),
                name="attempt_answer_position_between_1_and_10",
            ),
            models.CheckConstraint(
                condition=Q(is_correct__isnull=True)
                | Q(selected_option_key__isnull=False),
                name="attempt_answer_correct_requires_selection",
            ),
        ]
        ordering = ["position"]

    def __str__(self):
        return f"Ответ {self.position} попытки {self.attempt_id}"
