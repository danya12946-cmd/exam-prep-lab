from django.contrib.auth import get_user_model
from django.urls import reverse

from .helpers import CachedTestCase, load_demo_data

User = get_user_model()


class AuthAndTopicsTests(CachedTestCase):
    def setUp(self):
        super().setUp()
        load_demo_data()

    def test_signup_login_logout_flow(self):
        response = self.client.get("/accounts/signup/")
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            "/accounts/signup/",
            {
                "username": "newuser",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/")
        self.assertEqual(int(self.client.session["_auth_user_id"]), User.objects.get(username="newuser").pk)

        response = self.client.post(reverse("logout"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/accounts/login/")

        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith("/accounts/login/?next="))

        response = self.client.post(
            "/accounts/login/", {"username": "newuser", "password": "StrongPass123!"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/")

        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Алгебра")
        self.assertContains(response, "Геометрия")
        self.assertContains(response, "Основы программирования")
        self.assertContains(response, "Вопросов: 12", count=3)

    def test_signup_validation_messages(self):
        User.objects.create_user(username="taken", password="StrongPass123!")

        response = self.client.post(
            "/accounts/signup/",
            {"username": "taken", "password1": "AnotherPass123!", "password2": "AnotherPass123!"},
        )
        self.assertContains(response, "Имя пользователя уже занято")

        response = self.client.post(
            "/accounts/signup/", {"username": "user2", "password1": "", "password2": ""}
        )
        self.assertContains(response, "Пароль не может быть пустым")

        response = self.client.post(
            "/accounts/signup/", {"username": "user3", "password1": "12345", "password2": "12345"}
        )
        self.assertContains(response, "Пароль слишком простой")

        response = self.client.post(
            "/accounts/signup/",
            {"username": "user4", "password1": "StrongPass123!", "password2": "Different123!"},
        )
        self.assertContains(response, "Пароли не совпадают")

    def test_login_invalid_message(self):
        response = self.client.post(
            "/accounts/login/", {"username": "nobody", "password": "WrongPass123!"}
        )
        self.assertContains(response, "Неверное имя пользователя или пароль")

    def test_internal_pages_require_login(self):
        urls = [
            "/results/",
            "/topics/1/leaderboard/",
            "/attempts/1/question/",
        ]
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response.url.startswith("/accounts/login/?next="))

    def test_empty_topic_list_state(self):
        from exams.models import Topic

        Topic.objects.all().delete()
        user = User.objects.create_user(username="viewer2", password="StrongPass123!")
        self.client.force_login(user)
        response = self.client.get("/")
        self.assertContains(response, "Темы пока не добавлены")
