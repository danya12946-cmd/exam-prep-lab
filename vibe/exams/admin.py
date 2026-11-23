from django.contrib import admin
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet

from .models import AnswerOption, AttemptAnswer, Question, QuizAttempt, Topic


class AnswerOptionFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        active_forms = [
            form
            for form in self.forms
            if getattr(form, "cleaned_data", None)
            and not form.cleaned_data.get("DELETE", False)
        ]
        filled = sum(1 for form in active_forms if form.cleaned_data.get("text"))
        if filled < 2:
            raise ValidationError("У вопроса должно быть минимум 2 варианта ответа.")

        correct = sum(1 for form in active_forms if form.cleaned_data.get("is_correct"))
        if correct != 1:
            raise ValidationError("Отметьте ровно один правильный ответ.")


class AnswerOptionInline(admin.TabularInline):
    model = AnswerOption
    formset = AnswerOptionFormSet
    fields = ["text", "is_correct"]
    extra = 2
    min_num = 2
    validate_min = True


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ["name", "question_count", "created_at"]
    search_fields = ["name"]

    @admin.display(description="Вопросов")
    def question_count(self, obj):
        return obj.questions.count()


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ["short_text", "topic", "option_count"]
    list_filter = ["topic"]
    search_fields = ["text"]
    inlines = [AnswerOptionInline]

    @admin.display(description="Вопрос")
    def short_text(self, obj):
        return obj.text[:80]

    @admin.display(description="Вариантов")
    def option_count(self, obj):
        return obj.options.count()


class AttemptAnswerInline(admin.TabularInline):
    model = AttemptAnswer
    extra = 0
    fields = ["question_text", "selected_text", "correct_text", "is_correct"]
    readonly_fields = fields
    can_delete = False


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ["user", "topic", "score", "total_questions", "completed_at"]
    list_filter = ["topic"]
    readonly_fields = ["user", "topic", "score", "total_questions", "completed_at"]
    inlines = [AttemptAnswerInline]

    def has_add_permission(self, request):
        return False
