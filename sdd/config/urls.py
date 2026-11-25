from django.contrib import admin
from django.urls import include, path

from exams import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/signup/", views.signup, name="signup"),
    path("accounts/login/", views.exam_login, name="login"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("exams.urls")),
]
