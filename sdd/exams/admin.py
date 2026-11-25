from django.contrib import admin

from .forms import AnswerOptionFormSet
from .models import AnswerOption, Question, Topic


class AnswerOptionInline(admin.TabularInline):
    model = AnswerOption
    formset = AnswerOptionFormSet
    fields = ("position", "text", "is_correct")
    extra = 2


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    fields = ("slug", "title", "description")
    list_display = ("title", "slug")


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    fields = ("topic", "slug", "text")
    inlines = (AnswerOptionInline,)
    list_display = ("topic", "slug", "text")
    list_filter = ("topic",)
