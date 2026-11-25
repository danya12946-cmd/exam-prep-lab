from django.contrib.auth import get_user_model
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from .cache import (
    invalidate_all_leaderboards,
    invalidate_leaderboard,
    invalidate_topics_list,
    schedule_invalidation,
)
from .models import AnswerOption, Question, Topic

User = get_user_model()


def _using(instance, using=None):
    return using or instance._state.db


def _invalidate_topics_for_question(topic_ids, using=None):
    if any(topic_id is not None for topic_id in topic_ids):
        schedule_invalidation(invalidate_topics_list, using=using)


@receiver(post_save, sender=Topic, dispatch_uid="exams.topic.post_save")
def topic_saved(sender, instance, **kwargs):
    schedule_invalidation(invalidate_topics_list, using=_using(instance, kwargs.get("using")))


@receiver(post_delete, sender=Topic, dispatch_uid="exams.topic.post_delete")
def topic_deleted(sender, instance, **kwargs):
    using = _using(instance, kwargs.get("using"))
    schedule_invalidation(invalidate_topics_list, using=using)
    schedule_invalidation(invalidate_leaderboard, instance.pk, using=using)


@receiver(pre_save, sender=Question, dispatch_uid="exams.question.pre_save")
def question_pre_save(sender, instance, **kwargs):
    instance._old_topic_id = None
    if instance.pk:
        instance._old_topic_id = (
            Question.objects.filter(pk=instance.pk)
            .values_list("topic_id", flat=True)
            .first()
        )


@receiver(post_save, sender=Question, dispatch_uid="exams.question.post_save")
def question_saved(sender, instance, **kwargs):
    _invalidate_topics_for_question(
        [getattr(instance, "_old_topic_id", None), instance.topic_id],
        using=_using(instance, kwargs.get("using")),
    )


@receiver(post_delete, sender=Question, dispatch_uid="exams.question.post_delete")
def question_deleted(sender, instance, **kwargs):
    _invalidate_topics_for_question(
        [instance.topic_id], using=_using(instance, kwargs.get("using"))
    )


@receiver(pre_save, sender=AnswerOption, dispatch_uid="exams.answer_option.pre_save")
def answer_option_pre_save(sender, instance, **kwargs):
    instance._old_question_id = None
    if instance.pk:
        instance._old_question_id = (
            AnswerOption.objects.filter(pk=instance.pk)
            .values_list("question_id", flat=True)
            .first()
        )


@receiver(post_save, sender=AnswerOption, dispatch_uid="exams.answer_option.post_save")
def answer_option_saved(sender, instance, **kwargs):
    _invalidate_topics_for_question(
        [getattr(instance, "_old_question_id", None), instance.question_id],
        using=_using(instance, kwargs.get("using")),
    )


@receiver(post_delete, sender=AnswerOption, dispatch_uid="exams.answer_option.post_delete")
def answer_option_deleted(sender, instance, **kwargs):
    _invalidate_topics_for_question(
        [instance.question_id], using=_using(instance, kwargs.get("using"))
    )


@receiver(pre_save, sender=User, dispatch_uid="exams.user.pre_save")
def user_pre_save(sender, instance, **kwargs):
    instance._old_username = None
    if instance.pk:
        instance._old_username = (
            User.objects.filter(pk=instance.pk).values_list("username", flat=True).first()
        )


@receiver(post_save, sender=User, dispatch_uid="exams.user.post_save")
def user_saved(sender, instance, **kwargs):
    old_username = getattr(instance, "_old_username", None)
    if old_username is None or old_username == instance.username:
        return
    schedule_invalidation(
        invalidate_all_leaderboards, using=_using(instance, kwargs.get("using"))
    )
