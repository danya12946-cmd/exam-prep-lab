from django.core.management.base import BaseCommand
from django.db import transaction

from exams.models import AnswerOption, Question, Topic

DEMO_TOPICS = [
    {
        "slug": "algebra",
        "title": "Алгебра",
        "description": "Уравнения, неравенства, функции и последовательности.",
        "questions": [
            ("Чему равно значение выражения 2 + 3 × 4?", "14", "20", "24", "10"),
            ("Решите уравнение x + 7 = 12.", "5", "19", "-5", "7"),
            ("Чему равен корень уравнения 3x = 21?", "7", "18", "3", "63"),
            ("Как называется график функции y = 2x + 1?", "Прямая", "Парабола", "Окружность", "Гипербола"),
            ("Чему равно значение 5²?", "25", "10", "52", "125"),
            ("Сколько корней имеет уравнение x² = 9?", "Два", "Один", "Ноль", "Три"),
            ("Чему равен модуль числа -8?", "8", "-8", "0", "16"),
            ("Как записать произведение a × a × a?", "a³", "3a", "a²", "a⁴"),
            ("Решите неравенство x - 4 > 1.", "x > 5", "x < 5", "x > -5", "x < -5"),
            ("Чему равно 1/2 + 1/4?", "3/4", "1/6", "2/6", "1/2"),
            ("Как называют число перед переменной в выражении 7x?", "Коэффициент", "Степень", "Корень", "Множитель"),
            ("Чему равен периметр квадрата со стороной 6?", "24", "12", "36", "6"),
        ],
    },
    {
        "slug": "geometry",
        "title": "Геометрия",
        "description": "Плоские фигуры, углы, площади и объемы.",
        "questions": [
            ("Сколько сторон у треугольника?", "3", "4", "5", "2"),
            ("Сумма углов треугольника равна…", "180°", "90°", "360°", "270°"),
            ("Площадь прямоугольника 3 × 5 равна…", "15", "8", "16", "30"),
            ("Как называется окружность радиуса r?", "Геометрическая фигура", "Треугольник", "Квадрат", "Прямая"),
            ("Длина окружности равна…", "2πr", "πr²", "2r", "πr"),
            ("Сколько граней у куба?", "6", "8", "12", "4"),
            ("Объём куба со стороной 2 равен…", "8", "4", "6", "16"),
            ("Вертикальные углы…", "Равны", "Дополняют до 180°", "Суммируются до 90°", "Не существуют"),
            ("Площадь круга радиуса r равна…", "πr²", "2πr", "πr", "r²"),
            ("Диагональ прямоугольника делит его на…", "Два равных треугольника", "Два квадрата", "Три треугольника", "Четыре части"),
            ("Сколько вершин у пирамиды с квадратным основанием?", "5", "4", "6", "8"),
            ("Угол в квадрате равен…", "90°", "60°", "120°", "180°"),
        ],
    },
    {
        "slug": "programming",
        "title": "Основы программирования",
        "description": "Переменные, типы данных, условия и циклы.",
        "questions": [
            ("Какой тип данных хранит целые числа в Python?", "int", "str", "float", "bool"),
            ("Как объявить переменную со значением 5?", "x = 5", "int x = 5", "x := 5", "let x = 5"),
            ("Чему равен результат 7 // 2?", "3", "3.5", "4", "14"),
            ("Сколько элементов в списке [1, 2, 3]?", "3", "2", "4", "6"),
            ("Какой оператор проверяет равенство?", "==", "=", "===", "!="),
            ("Как называется блок кода после if?", "Ветка", "Цикл", "Функция", "Класс"),
            ("Какой цикл выполняется известное число раз?", "for", "while", "do", "repeat"),
            ("Что вернёт len('exam')?", "4", "5", "3", "exam"),
            ("Какой тип результата выражения 3 > 2?", "bool", "int", "str", "float"),
            ("Как вызвать функцию print?", "print('текст')", "print = 'текст'", "call print", "echo 'текст'"),
            ("Индекс первого элемента списка в Python равен…", "0", "1", "-1", "2"),
            ("Как добавить элемент в конец списка?", "append", "insert", "push", "add"),
        ],
    },
]


class Command(BaseCommand):
    help = "Идемпотентно загрузить демо-темы, вопросы и варианты ответов"

    @transaction.atomic
    def handle(self, *args, **options):
        topics_created = 0
        questions_created = 0
        topics_existing = 0
        questions_existing = 0

        for topic_data in DEMO_TOPICS:
            topic, topic_created = Topic.objects.get_or_create(
                slug=topic_data["slug"],
                defaults={
                    "title": topic_data["title"],
                    "description": topic_data["description"],
                },
            )
            if topic_created:
                topics_created += 1
            else:
                topics_existing += 1

            for index, (text, correct, *wrong) in enumerate(topic_data["questions"], 1):
                question, question_created = Question.objects.get_or_create(
                    topic=topic,
                    slug=f"demo-{topic_data['slug']}-q{index:02d}",
                    defaults={"text": text},
                )
                if question_created:
                    questions_created += 1
                else:
                    questions_existing += 1

                options = [(correct, True)] + [(item, False) for item in wrong]
                for position, (option_text, is_correct) in enumerate(options, 1):
                    AnswerOption.objects.get_or_create(
                        question=question,
                        position=position,
                        defaults={"text": option_text, "is_correct": is_correct},
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"Тем создано: {topics_created}, уже существовало: {topics_existing}. "
                f"Вопросов создано: {questions_created}, уже существовало: {questions_existing}."
            )
        )
