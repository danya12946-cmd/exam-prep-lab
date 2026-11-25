from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

User = get_user_model()


class SignUpForm(forms.Form):
    username = forms.CharField(max_length=150, label="Имя пользователя")
    password1 = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput,
        error_messages={"required": "Пароль не может быть пустым"},
    )
    password2 = forms.CharField(
        label="Повторите пароль",
        widget=forms.PasswordInput,
        error_messages={"required": "Пароль не может быть пустым"},
    )

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("Имя пользователя уже занято")
        return username

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if not password1:
            return password2
        if password1 != password2:
            raise ValidationError("Пароли не совпадают")
        try:
            validate_password(password1)
        except ValidationError:
            raise ValidationError("Пароль слишком простой") from None
        return password2

    def save(self):
        return User.objects.create_user(
            username=self.cleaned_data["username"],
            password=self.cleaned_data["password1"],
        )


class LoginForm(AuthenticationForm):
    error_messages = {
        **AuthenticationForm.error_messages,
        "invalid_login": "Неверное имя пользователя или пароль",
    }


class StartAttemptForm(forms.Form):
    topic_id = forms.IntegerField(
        error_messages={
            "required": "Тема не найдена",
            "invalid": "Тема не найдена",
        }
    )

    def clean_topic_id(self):
        from .models import Topic

        topic = Topic.objects.filter(pk=self.cleaned_data["topic_id"]).first()
        if topic is None:
            raise ValidationError("Тема не найдена")
        if not topic.questions.exists():
            raise ValidationError("В теме нет вопросов")
        return topic


class AnswerForm(forms.Form):
    option_key = forms.CharField(
        error_messages={"required": "Выберите один из предложенных вариантов"}
    )

    def __init__(self, *args, answer=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.answer = answer

    def clean_option_key(self):
        option_key = self.cleaned_data["option_key"]
        valid_keys = {option["key"] for option in self.answer.options_snapshot}
        if option_key not in valid_keys:
            raise ValidationError("Выберите один из предложенных вариантов")
        return option_key
