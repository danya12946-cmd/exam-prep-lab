from decimal import Decimal, ROUND_HALF_UP

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from .cache import invalidate_attempt_result, schedule_invalidation
from .models import Attempt, AttemptAnswer, Question

User = get_user_model()


def start_attempt(topic, user):
    questions = list(
        Question.objects.filter(topic=topic)
        .prefetch_related("options")
        .order_by("?")[:10]
    )
    if not questions:
        raise ValueError("В теме нет вопросов")

    with transaction.atomic():
        attempt = Attempt.objects.create(
            user=user,
            topic=topic,
            topic_id_snapshot=topic.id,
            topic_title_snapshot=topic.title,
            status=Attempt.Status.IN_PROGRESS,
            question_count=len(questions),
            correct_count=0,
            percent=0,
        )
        for position, question in enumerate(questions, 1):
            options = list(question.options.all())
            answer = AttemptAnswer.objects.create(
                attempt=attempt,
                position=position,
                source_question_id=question.id,
                question_text_snapshot=question.text,
            )
            option_map = [
                {"key": f"a{answer.pk}o{option.position}", "text": option.text}
                for option in options
            ]
            correct_option = next(option for option in options if option.is_correct)
            answer.options_snapshot = option_map
            answer.correct_option_key = f"a{answer.pk}o{correct_option.position}"
            answer.correct_text_snapshot = correct_option.text
            answer.save(
                update_fields=[
                    "options_snapshot",
                    "correct_option_key",
                    "correct_text_snapshot",
                ]
            )
    return attempt


def submit_answer(attempt, option_key):
    current = (
        attempt.answers.filter(selected_option_key__isnull=True)
        .order_by("position")
        .first()
    )
    if current is None:
        return "Ответ уже сохранён"

    valid_keys = {option["key"] for option in current.options_snapshot}
    if option_key not in valid_keys:
        for answered in attempt.answers.exclude(pk=current.pk).exclude(
            selected_option_key__isnull=True
        ):
            if any(option["key"] == option_key for option in answered.options_snapshot):
                return "Ответ уже сохранён"
        return "Выберите один из предложенных вариантов"

    selected_text = next(
        option["text"] for option in current.options_snapshot if option["key"] == option_key
    )
    updated = AttemptAnswer.objects.filter(
        pk=current.pk,
        selected_option_key__isnull=True,
        attempt__user=attempt.user,
    ).update(
        selected_option_key=option_key,
        selected_text_snapshot=selected_text,
        is_correct=option_key == current.correct_option_key,
        answered_at=timezone.now(),
    )
    if not updated:
        return "Ответ уже сохранён"

    if not attempt.answers.filter(selected_option_key__isnull=True).exists():
        complete_attempt(attempt)
    return None


def complete_attempt(attempt):
    with transaction.atomic():
        locked = Attempt.objects.select_for_update().get(pk=attempt.pk)
        if locked.status == Attempt.Status.COMPLETED:
            return locked
        answers = list(locked.answers.all())
        correct_count = sum(1 for answer in answers if answer.is_correct)
        percent = int(
            (Decimal(correct_count * 100) / Decimal(locked.question_count)).quantize(
                Decimal("1"), rounding=ROUND_HALF_UP
            )
        )
        locked.status = Attempt.Status.COMPLETED
        locked.completed_at = timezone.now()
        locked.correct_count = correct_count
        locked.percent = percent
        locked.save(
            update_fields=["status", "completed_at", "correct_count", "percent"]
        )
        schedule_invalidation(
            invalidate_attempt_result,
            locked.user_id,
            locked.topic_id_snapshot,
        )
    return locked


def build_topic_leaderboard(topic_id):
    attempts = Attempt.objects.filter(
        status=Attempt.Status.COMPLETED,
        topic_id_snapshot=topic_id,
    )
    grouped = list(attempts.values("user_id").annotate(best_percent=Max("percent")))
    usernames = dict(
        User.objects.filter(id__in=[row["user_id"] for row in grouped]).values_list(
            "id", "username"
        )
    )
    ranked = []
    for row in grouped:
        completed_at = (
            attempts.filter(user_id=row["user_id"], percent=row["best_percent"])
            .order_by("completed_at", "id")
            .values_list("completed_at", flat=True)
            .first()
        )
        ranked.append(
            (
                -row["best_percent"],
                completed_at,
                usernames.get(row["user_id"], ""),
                row["best_percent"],
            )
        )
    ranked.sort()
    return [
        {
            "place": place,
            "username": username,
            "percent": percent,
        }
        for place, (_, _, username, percent) in enumerate(ranked[:10], 1)
    ]
