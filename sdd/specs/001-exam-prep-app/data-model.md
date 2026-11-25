# Модель данных

**Документ**: Phase 1 | **Spec**: `spec.md` | **Связанные контракты**: `contracts/http.md`, `contracts/cache.md`

## Обзор

Живой контент (темы, вопросы, варианты) отделён от снимков в попытках. Попытка создаётся с полным снимком отобранных вопросов и вариантов; завершение фиксирует ответы и результат только по этому снимку. Поэтому admin-правки и удаление контента не меняют историю. Все названия полей и классов — на английском.

## Сущности

### User (встроенная модель Django)

| Поле | Тип | Назначение |
|---|---|---|
| `id` | PK | Идентификатор |
| `username` | `CharField`, unique | Имя пользователя, используется в лидерборде |
| `password` | `CharField` | Хеш пароля |
| `is_staff` | `BooleanField` | Доступ к Django admin |
| `is_active` | `BooleanField` | Разрешение входа |

**Связи**: `attempts` — все попытки пользователя (`related_name="attempts"`).

**Правила**: уникальность имени и безопасность пароля обеспечиваются `django.contrib.auth`; внутренние страницы требуют аутентификации; разбор и история фильтруются по `user=request.user`. Смена `username` инвалидирует кэш лидербордов.

### Topic

| Поле | Тип | Назначение |
|---|---|---|
| `id` | PK | Идентификатор |
| `slug` | `SlugField`, unique | Стабильный ключ демо-данных и URL-ов |
| `title` | `CharField(200)` | Название темы |
| `description` | `TextField` | Описание темы |
| `created_at` | `DateTimeField(auto_now_add)` | Дата создания |

**Связи**: `questions` — вопросы темы (`CASCADE`); `attempts` — попытки по теме (`SET_NULL`, `null=True`).

**Вычисляемое поле**: `question_count` — `Count("questions")`, попадает в кэш `topics:list`.

**Ограничения**: `slug` уникален на уровне БД; `title` и `description` не пустые. Любое `post_save`/`post_delete` темы инвалидирует `topics:list`; удаление дополнительно инвалидирует `leaderboard:topic:<id>`.

### Question

| Поле | Тип | Назначение |
|---|---|---|
| `id` | PK | Идентификатор |
| `topic` | `ForeignKey(Topic, CASCADE)` | Тема вопроса |
| `slug` | `SlugField` | Стабильный ключ в пределах темы |
| `text` | `TextField` | Формулировка вопроса |
| `created_at`, `updated_at` | `DateTimeField` | Время создания/правки |

**Связи**: `options` — варианты ответа (`related_name="options"`, `CASCADE`).

**Ограничения**:
- `UniqueConstraint(fields=["topic", "slug"])`;
- `text` не пустой;
- количество вариантов от 2 до 6 и ровно один с `is_correct=True` гарантируются отложенным PostgreSQL constraint trigger из миграции;
- inline formset в admin даёт понятные русские сообщения до обращения к БД.

Изменение или удаление вопроса инвалидирует `topics:list` для старого и нового `topic_id`.

### AnswerOption

| Поле | Тип | Назначение |
|---|---|---|
| `id` | PK | Идентификатор |
| `question` | `ForeignKey(Question, CASCADE)` | Вопрос |
| `position` | `PositiveSmallIntegerField` | Порядок 1–6 |
| `text` | `CharField(255)` | Текст варианта |
| `is_correct` | `BooleanField(default=False)` | Признак правильного варианта |

**Ограничения**:
- `UniqueConstraint(fields=["question", "position"])`;
- `CheckConstraint` на `1 <= position <= 6`;
- partial unique index `UNIQUE (question_id) WHERE is_correct = TRUE` защищает от двух правильных вариантов при конкурентной записи;
- отложенный trigger проверяет 2–6 вариантов и ровно один правильный в конце транзакции.

Изменение или удаление варианта инвалидирует `topics:list`.

### Attempt

| Поле | Тип | Назначение |
|---|---|---|
| `id` | PK | Идентификатор попытки |
| `user` | `ForeignKey(User, CASCADE)` | Владелец |
| `topic` | `ForeignKey(Topic, SET_NULL, null=True)` | Тема, если ещё существует |
| `topic_id_snapshot` | `PositiveIntegerField` | ID темы на момент старта |
| `topic_title_snapshot` | `CharField(200)` | Название темы на момент старта |
| `status` | `CharField(choices=IN_PROGRESS/COMPLETED)` | Статус |
| `started_at` | `DateTimeField` | Начало попытки |
| `completed_at` | `DateTimeField(null=True)` | Завершение, только для `COMPLETED` |
| `question_count` | `PositiveSmallIntegerField` | Число вопросов 1–10 |
| `correct_count` | `PositiveSmallIntegerField` | Число верных ответов |
| `percent` | `PositiveSmallIntegerField` | Процент, округлённый до целого |

**Связи**: `answers` — снимки вопросов и ответов (`related_name="answers"`, `CASCADE`).

**Ограничения базы**:
- `1 <= question_count <= 10`;
- `0 <= correct_count <= question_count`;
- `0 <= percent <= 100`;
- `(status = COMPLETED AND completed_at IS NOT NULL) OR (status = IN_PROGRESS AND completed_at IS NULL)`;
- индексы `(user, status, -started_at)` для истории и `(topic, status, -percent, completed_at)` для лидерборда.

**Правила доступа**: каждая операция с попыткой использует фильтр по владельцу; чужой объект возвращает 404 без раскрытия содержимого.

### AttemptAnswer

| Поле | Тип | Назначение |
|---|---|---|
| `id` | PK | Идентификатор записи |
| `attempt` | `ForeignKey(Attempt, CASCADE)` | Попытка |
| `position` | `PositiveSmallIntegerField` | Порядок 1–10 |
| `source_question_id` | `PositiveIntegerField` | ID исходного вопроса (только для уникальности) |
| `question_text_snapshot` | `TextField` | Формулировка на момент старта |
| `options_snapshot` | `JSONField` | Список `{"key": str, "text": str}` на момент старта |
| `selected_option_key` | `CharField(16, null=True)` | Ключ выбранного варианта; `NULL` = ответ не дан |
| `selected_text_snapshot` | `TextField(blank=True)` | Текст выбранного варианта |
| `correct_option_key` | `CharField(16, blank=True)` | Ключ правильного варианта на момент старта |
| `correct_text_snapshot` | `TextField(blank=True)` | Текст правильного варианта |
| `is_correct` | `BooleanField(null=True)` | Верность ответа; `NULL`, пока нет ответа |
| `answered_at` | `DateTimeField(null=True)` | Время ответа |

**Ограничения базы**:
- `UniqueConstraint(fields=["attempt", "position"])`;
- `UniqueConstraint(fields=["attempt", "source_question_id"])`;
- `CheckConstraint` на `1 <= position <= 10`;
- `is_correct IS NULL OR selected_option_key IS NOT NULL` (нельзя отметить верность без ответа).

**Инвариант сервиса**: в `COMPLETED`-попытке все `selected_option_key` заполнены, а `correct_count`/`percent` пересчитаны из `is_correct`. Инвариант проверяется тестами и блокировкой `select_for_update()` при завершении.

## Связи

```text
User ──< Attempt >── Topic ──< Question ──< AnswerOption
                  └──< AttemptAnswer (снимки, без FK на живые вопросы)
```

`Attempt.topic` может стать `NULL` после удаления темы, но `topic_id_snapshot` и `topic_title_snapshot` сохраняют подпись в истории.

## Переходы состояния Attempt

| Действие | Из | В | Что происходит |
|---|---|---|---|
| `start_attempt(topic)` | — | `IN_PROGRESS` | Проверка наличия вопросов; случайный выбор до 10; создание снимков; кэш не меняется |
| `submit_answer(attempt, option_key)` | `IN_PROGRESS` | `IN_PROGRESS` или `COMPLETED` | Условное обновление текущего ответа; повторный ответ отклоняется; на последнем вопросе вызывается `complete_attempt` |
| `complete_attempt(attempt)` | `IN_PROGRESS` | `COMPLETED` | `select_for_update`, подсчёт по снимкам, `ROUND_HALF_UP`, установка `completed_at`, инвалидация `user:best` и `leaderboard:topic` после commit |
| Прервать тест | `IN_PROGRESS` | `IN_PROGRESS` | Явного перехода нет; попытка остаётся в базе, но исключается из истории завершённых, лучших результатов и лидерборда |

## Производные выборки

- **Список тем**: `Topic.objects.annotate(question_count=Count("questions"))`, результат кэшируется целиком.
- **Мои результаты — история**: завершённые попытки пользователя по `completed_at desc`; читается из БД напрямую.
- **Лучшие результаты пользователя**: максимум `percent` по завершённым попыткам, сгруппированный по `topic_id_snapshot`; при нескольких попытках с одинаковым максимальным `percent` используется `MIN(completed_at)`; кэшируется.
- **Лидерборд темы**: по завершённым попыткам выбрать лучший `percent` на пользователя для пары `(user, topic_id_snapshot)`; при равенстве процентов используется `MIN(completed_at)` среди попыток с максимальным `percent`; сортировка `percent desc`, `completed_at asc`, `username asc`, `LIMIT 10`; кэшируется.
- **Разбор попытки**: только `AttemptAnswer`, доступ проверяется по владельцу; не кэшируется.
