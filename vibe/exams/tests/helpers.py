from exams.models import AnswerOption, Question


def create_question(topic, text, correct_index=0, option_count=4):
    question = Question.objects.create(topic=topic, text=text)
    for index in range(option_count):
        AnswerOption.objects.create(
            question=question,
            text=f"{text} — вариант {index + 1}",
            is_correct=index == correct_index,
        )
    return question
