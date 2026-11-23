from django.core.management.base import BaseCommand
from django.db import transaction

from exams.models import AnswerOption, Question, Topic

DEMO_DATA = {
    "Python": {
        "description": "Базовый синтаксис, типы данных и стандартная библиотека Python.",
        "questions": [
            (
                "Какой тип данных хранит последовательность символов?",
                [("str", True), ("int", False), ("list", False), ("dict", False)],
            ),
            (
                "Какой оператор проверяет принадлежность элемента к коллекции?",
                [("in", True), ("is", False), ("not", False), ("and", False)],
            ),
            (
                "Что вернёт вызов len([1, 2, 3])?",
                [("3", True), ("2", False), ("4", False), ("None", False)],
            ),
            (
                "Какой метод добавляет элемент в конец списка?",
                [("append", True), ("insert", False), ("extend", False), ("pop", False)],
            ),
            (
                "Какое ключевое слово создаёт генератор?",
                [("yield", True), ("return", False), ("lambda", False), ("global", False)],
            ),
            (
                "Какой из этих типов данных неизменяемый?",
                [("tuple", True), ("list", False), ("dict", False), ("set", False)],
            ),
            (
                "Какой блок обрабатывает исключение?",
                [("except", True), ("finally", False), ("else", False), ("elif", False)],
            ),
            (
                "Что делает функция sorted()?",
                [
                    ("Возвращает новый отсортированный список", True),
                    ("Изменяет список на месте", False),
                    ("Удаляет дубликаты", False),
                    ("Перемешивает элементы", False),
                ],
            ),
            (
                "Как записывается аннотация типа для целого числа?",
                [("int", True), ("Integer", False), ("<int>", False), ("number", False)],
            ),
            (
                "Что вернёт словарь методом get('missing') для отсутствующего ключа?",
                [("None", True), ("0", False), ("''", False), ("KeyError", False)],
            ),
            (
                "Какой метод словаря возвращает список пар ключ-значение?",
                [("items", True), ("keys", False), ("values", False), ("get", False)],
            ),
            (
                "Что вернёт range(3)?",
                [
                    ("Последовательность 0, 1, 2", True),
                    ("Список 1, 2, 3", False),
                    ("Список 0, 1, 2, 3", False),
                    ("Только число 3", False),
                ],
            ),
        ],
    },
    "Базы данных": {
        "description": "Реляционные базы данных, SQL и основы проектирования схемы.",
        "questions": [
            (
                "Что делает первичный ключ?",
                [
                    ("Уникально идентифицирует запись", True),
                    ("Хранит только дату", False),
                    ("Всегда равен внешнему ключу", False),
                    ("Запрещает обновление таблицы", False),
                ],
            ),
            (
                "Какой язык используется для запросов к реляционным БД?",
                [("SQL", True), ("HTML", False), ("JSON", False), ("YAML", False)],
            ),
            (
                "Что делает JOIN в SQL?",
                [
                    ("Объединяет строки таблиц по условию", True),
                    ("Создаёт новую базу", False),
                    ("Удаляет дубликаты", False),
                    ("Изменяет тип колонки", False),
                ],
            ),
            (
                "Какое поле Django реализует связь «один ко многим»?",
                [("ForeignKey", True), ("CharField", False), ("ManyToManyField", False), ("BooleanField", False)],
            ),
            (
                "Для чего нужен индекс в базе данных?",
                [
                    ("Ускоряет поиск и фильтрацию", True),
                    ("Уменьшает размер таблицы", False),
                    ("Заменяет первичный ключ", False),
                    ("Шифрует данные", False),
                ],
            ),
            (
                "Какая команда SQL удаляет таблицу?",
                [("DROP TABLE", True), ("DELETE TABLE", False), ("REMOVE TABLE", False), ("TRUNCATE TABLE", False)],
            ),
            (
                "Что такое транзакция?",
                [
                    ("Набор операций, выполняемых как единое целое", True),
                    ("Один столбец таблицы", False),
                    ("Резервная копия файла", False),
                    ("Ограничение на длину строки", False),
                ],
            ),
            (
                "Какой уровень изоляции в PostgreSQL используется по умолчанию?",
                [("Read Committed", True), ("Read Uncommitted", False), ("Repeatable Read", False), ("Serializable", False)],
            ),
            (
                "Какая функция SQL подсчитывает количество строк?",
                [("COUNT", True), ("SUM", False), ("MAX", False), ("ROUND", False)],
            ),
            (
                "Что означает буква C в аббревиатуре ACID?",
                [("Consistency", True), ("Cache", False), ("Connection", False), ("Commit", False)],
            ),
            (
                "Какой тип PostgreSQL предназначен для UUID?",
                [("uuid", True), ("text", False), ("serial", False), ("bytea", False)],
            ),
            (
                "Что делает предложение GROUP BY?",
                [
                    ("Группирует строки для агрегации", True),
                    ("Сортирует результат", False),
                    ("Ограничивает число строк", False),
                    ("Объединяет таблицы", False),
                ],
            ),
        ],
    },
    "Веб и Docker": {
        "description": "HTTP, Git и запуск приложения в контейнерах.",
        "questions": [
            (
                "Какой HTTP-код означает «Не найдено»?",
                [("404", True), ("200", False), ("301", False), ("500", False)],
            ),
            (
                "Какой метод HTTP обычно используют для создания ресурса?",
                [("POST", True), ("GET", False), ("HEAD", False), ("OPTIONS", False)],
            ),
            (
                "Что делает Docker Compose?",
                [
                    ("Описывает и запускает несколько сервисов", True),
                    ("Компилирует код Python", False),
                    ("Управляет миграциями Django", False),
                    ("Форматирует SQL-запросы", False),
                ],
            ),
            (
                "Какой файл Docker Compose использует по умолчанию?",
                [("compose.yaml", True), ("Dockerfile", False), ("requirements.txt", False), ("manage.py", False)],
            ),
            (
                "Что делает команда docker compose up --build?",
                [
                    ("Собирает образы и запускает сервисы", True),
                    ("Только удаляет контейнеры", False),
                    ("Создаёт миграции", False),
                    ("Проверяет синтаксис YAML", False),
                ],
            ),
            (
                "От чего защищает CSRF-токен?",
                [
                    ("От подделки межсайтовых запросов", True),
                    ("От утечки пароля из базы", False),
                    ("От медленного интернета", False),
                    ("От ошибок в SQL", False),
                ],
            ),
            (
                "Что показывает команда git status?",
                [
                    ("Состояние рабочего каталога и индекса", True),
                    ("Список всех коммитов", False),
                    ("Настройки удалённого репозитория", False),
                    ("Размер репозитория", False),
                ],
            ),
            (
                "Какой файл содержит инструкции для сборки образа Docker?",
                [("Dockerfile", True), ("compose.yaml", False), (".gitignore", False), ("settings.py", False)],
            ),
            (
                "Что делает команда git commit?",
                [
                    ("Сохраняет подготовленные изменения в истории", True),
                    ("Отправляет изменения на сервер", False),
                    ("Создаёт новую ветку", False),
                    ("Удаляет файлы из репозитория", False),
                ],
            ),
            (
                "Какой порт по умолчанию использует HTTPS?",
                [("443", True), ("80", False), ("5432", False), ("8000", False)],
            ),
            (
                "Что делает docker compose logs -f web?",
                [
                    ("Показывает логи сервиса web в реальном времени", True),
                    ("Перезапускает сервис web", False),
                    ("Открывает оболочку контейнера", False),
                    ("Удаляет логи", False),
                ],
            ),
            (
                "В каком файле Django project хранятся настройки по умолчанию?",
                [("settings.py", True), ("models.py", False), ("views.py", False), ("urls.py", False)],
            ),
        ],
    },
}


class Command(BaseCommand):
    help = "Загружает демо-темы и вопросы (безопасно повторять)"

    @transaction.atomic
    def handle(self, *args, **options):
        created_questions = 0
        created_options = 0

        for topic_name, payload in DEMO_DATA.items():
            topic, _ = Topic.objects.get_or_create(
                name=topic_name,
                defaults={"description": payload["description"]},
            )

            for text, options in payload["questions"]:
                question, question_created = Question.objects.get_or_create(
                    topic=topic,
                    text=text,
                )
                if question_created:
                    created_questions += 1

                question.options.update(is_correct=False)
                for option_text, is_correct in options:
                    _, option_created = AnswerOption.objects.update_or_create(
                        question=question,
                        text=option_text,
                        defaults={"is_correct": is_correct},
                    )
                    if option_created:
                        created_options += 1

                question.options.exclude(
                    text__in=[option_text for option_text, _ in options]
                ).delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Демо-данные загружены: {len(DEMO_DATA)} тем, "
                f"новых вопросов: {created_questions}, новых вариантов: {created_options}."
            )
        )
