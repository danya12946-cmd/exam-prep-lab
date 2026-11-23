import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def required_env(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise ImproperlyConfigured(f"Environment variable {name} is required")
    return value


def bool_env(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def csv_env(name, default):
    value = os.environ.get(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


SECRET_KEY = required_env("DJANGO_SECRET_KEY")
DEBUG = bool_env("DJANGO_DEBUG", default=False)

ALLOWED_HOSTS = csv_env(
    "DJANGO_ALLOWED_HOSTS",
    "localhost,127.0.0.1,testserver,.app.github.dev",
)
CSRF_TRUSTED_ORIGINS = csv_env(
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    "http://localhost:8000,http://127.0.0.1:8000,https://*.app.github.dev",
)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "exams",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "exam_prep"),
        "USER": os.environ.get("POSTGRES_USER", "exam_prep"),
        "PASSWORD": required_env("POSTGRES_PASSWORD"),
        "HOST": os.environ.get("POSTGRES_HOST", "db"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "ru-ru"
TIME_ZONE = "Europe/Moscow"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "topics"
LOGOUT_REDIRECT_URL = "home"

QUIZ_QUESTION_COUNT = 10
