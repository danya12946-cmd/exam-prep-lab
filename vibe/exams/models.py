from django.conf import settings
from django.db import models
from django.db.models import Q


class Topic(models.Model):
    name = models.CharField("Название", max_length=120, unique=True)
    description = models.TextField("Описание", blank=True)
    created_at = models.DateTimeField("Создана", auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Тема"
        verbose_name_plural = "Темы"

    def __str__(self):
        return self.name


class Question(models.Model):
    topic = models.ForeignKey(
        Topic,
        on_delete=models.CASCADE,
        related_name="questions",
        verbose_name="Тема",
    )
    text = models.TextField("Текст вопроса")
    created_at = models.DateTimeField("Создан", auto_now_add=True)

    class Meta:
        ordering = ["id"]
        verbose_name = "Вопрос"
        verbose_name_plural = "Вопросы"
        constraints = [
            models.UniqueConstraint(
                fields=["topic", "text"],
                name="unique_question_per_topic",
            )
        ]

    def __str__(self):
        return self.text[:80]

    def correct_option(self):
        return self.options.filter(is_correct=True).first()


class AnswerOption(models.Model):
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="options",
        verbose_name="Вопрос",
    )
    text = models.CharField("Текст варианта", max_length=255)
    is_correct = models.BooleanField("Правильный ответ", default=False)

    class Meta:
        ordering = ["id"]
        verbose_name = "Вариант ответа"
        verbose_name_plural = "Варианты ответа"
        constraints = [
            models.UniqueConstraint(
                fields=["question"],
                condition=Q(is_correct=True),
                name="unique_correct_option_per_question",
            )
        ]

    def __str__(self):
        return self.text


class QuizAttempt(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="quiz_attempts",
        verbose_name="Пользователь",
    )
    topic = models.ForeignKey(
        Topic,
        on_delete=models.PROTECT,
        related_name="attempts",
        verbose_name="Тема",
    )
    score = models.PositiveIntegerField("Правильных ответов")
    total_questions = models.PositiveIntegerField("Всего вопросов")
    completed_at = models.DateTimeField("Завершена", auto_now_add=True)

    class Meta:
        ordering = ["-completed_at"]
        verbose_name = "Попытка"
        verbose_name_plural = "Попытки"

    def __str__(self):
        return f"{self.user}: {self.score}/{self.total_questions}"

    @property
    def percent(self):
        if not self.total_questions:
            return 0
        return round(self.score * 100 / self.total_questions)


class AttemptAnswer(models.Model):
    attempt = models.ForeignKey(
        QuizAttempt,
        on_delete=models.CASCADE,
        related_name="answers",
        verbose_name="Попытка",
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attempt_answers",
        verbose_name="Вопрос",
    )
    question_text = models.TextField("Текст вопроса")
    selected_text = models.CharField("Выбранный ответ", max_length=255)
    correct_text = models.CharField("Правильный ответ", max_length=255)
    is_correct = models.BooleanField("Верно", default=False)
    order = models.PositiveSmallIntegerField("Порядок", default=0)

    class Meta:
        ordering = ["order"]
        verbose_name = "Ответ в попытке"
        verbose_name_plural = "Ответы в попытках"

    def __str__(self):
        return self.question_text[:80]
