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
