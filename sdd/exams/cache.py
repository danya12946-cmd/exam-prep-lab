import logging
from functools import partial

from django.core.cache import cache
from django.db import transaction
from django.db.models import Count, Max
from redis.exceptions import RedisError

from .models import Attempt, Topic

logger = logging.getLogger("exams.cache")

SENTINEL = object()
CACHE_TTL = 300

TOPICS_LIST_KEY = "topics:list"
LEADERBOARD_KEY_PREFIX = "leaderboard:topic:"
USER_BEST_KEY_PREFIX = "user:best:"


def leaderboard_key(topic_id):
    return f"{LEADERBOARD_KEY_PREFIX}{topic_id}"


def user_best_key(user_id):
    return f"{USER_BEST_KEY_PREFIX}{user_id}"


def safe_cache_get(key):
    try:
        return cache.get(key, SENTINEL)
    except (RedisError, OSError):
        logger.warning("Не удалось прочитать кэш по ключу %s", key, exc_info=True)
        return SENTINEL


def safe_cache_set(key, value, timeout=CACHE_TTL):
    try:
        cache.set(key, value, timeout)
    except (RedisError, OSError):
        logger.warning("Не удалось записать кэш по ключу %s", key, exc_info=True)


def safe_cache_delete_many(keys):
    keys = list(keys)
    if not keys:
        return
    try:
        cache.delete_many(keys)
    except (RedisError, OSError):
        logger.warning("Не удалось удалить ключи кэша: %s", keys, exc_info=True)


def schedule_invalidation(function, *args, using=None):
    transaction.on_commit(partial(function, *args), using=using, robust=True)


def invalidate_direct_write(keys, using=None):
    schedule_invalidation(safe_cache_delete_many, list(keys), using=using)


def invalidate_topics_list(using=None):
    safe_cache_delete_many([TOPICS_LIST_KEY])


def invalidate_leaderboard(topic_id, using=None):
    safe_cache_delete_many([leaderboard_key(topic_id)])


def invalidate_user_best(user_id, using=None):
    safe_cache_delete_many([user_best_key(user_id)])


def invalidate_all_leaderboards(using=None):
    topic_ids = set(Topic.objects.using(using).values_list("id", flat=True))
    topic_ids.update(
        Attempt.objects.using(using)
        .values_list("topic_id_snapshot", flat=True)
        .distinct()
    )
    safe_cache_delete_many([leaderboard_key(topic_id) for topic_id in topic_ids])


def invalidate_attempt_result(user_id, topic_id, using=None):
    invalidate_user_best(user_id)
    invalidate_leaderboard(topic_id)


def get_topics():
    """Cache-aside: topics:list инвалидируется сигналами Topic/Question/AnswerOption
    и явными вызовами для массовых/raw-записей."""
    cached = safe_cache_get(TOPICS_LIST_KEY)
    if cached is not SENTINEL:
        return cached
    topics = list(
        Topic.objects.annotate(question_count=Count("questions"))
        .values("id", "slug", "title", "description", "question_count")
        .order_by("id")
    )
    safe_cache_set(TOPICS_LIST_KEY, topics)
    return topics


def get_user_best(user_id):
    """Cache-aside: user:best:<id> инвалидируется при завершении попытки."""
    key = user_best_key(user_id)
    cached = safe_cache_get(key)
    if cached is not SENTINEL:
        return cached
    grouped = list(
        Attempt.objects.filter(
            user_id=user_id,
            status=Attempt.Status.COMPLETED,
        )
        .values("topic_id_snapshot", "topic_title_snapshot")
        .annotate(best_percent=Max("percent"))
        .order_by("topic_id_snapshot")
    )
    result = []
    for row in grouped:
        best_attempt = (
            Attempt.objects.filter(
                user_id=user_id,
                status=Attempt.Status.COMPLETED,
                topic_id_snapshot=row["topic_id_snapshot"],
                percent=row["best_percent"],
            )
            .order_by("completed_at", "id")
            .first()
        )
        result.append(
            {
                "topic_id": row["topic_id_snapshot"],
                "topic_title": row["topic_title_snapshot"],
                "best_percent": row["best_percent"],
                "completed_at": best_attempt.completed_at if best_attempt else None,
            }
        )
    safe_cache_set(key, result)
    return result


def get_topic_leaderboard(topic_id):
    """Cache-aside: leaderboard:topic:<id> инвалидируется при завершении попытки,
    удалении темы или смене username; TTL 300 с — страховка на время недоступности Valkey."""
    key = leaderboard_key(topic_id)
    cached = safe_cache_get(key)
    if cached is not SENTINEL:
        return cached
    from .services import build_topic_leaderboard

    result = build_topic_leaderboard(topic_id)
    safe_cache_set(key, result)
    return result
