---

description: "Task list for feature implementation: Веб-приложение для подготовки к экзамену"
---

# Tasks: Веб-приложение для подготовки к экзамену

**Input**: Design documents from `/specs/001-exam-prep-app/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md, `.specify/memory/constitution.md`

**Tests**: тесты обязательны по принципу II конституции и плану (`python manage.py test`); задачи тестов идут перед реализацией в каждой истории.

**Organization**: задачи сгруппированы по пользовательским историям (US1–US5), каждая фаза — самостоятельно тестируемый инкремент.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: можно выполнять параллельно (разные файлы, нет зависимостей от незавершённых задач)
- **[Story]**: принадлежность к пользовательской истории (US1–US5); в фазах Setup, Foundational и Polish метка отсутствует
- все пути — относительно корня `sdd/`

## Path Conventions

- Django-проект в корне `sdd/`: `config/`, `exams/`, `specs/`
- Тесты: `exams/tests/`
- Шаблоны: `exams/templates/exams/`
- Собственная статика: `static/css/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: воспроизводимый каркас проекта по `plan.md` и `research.md`

- [ ] T001 Create project structure in sdd/ per plan.md: config/, exams/migrations/, exams/management/commands/, exams/templates/exams/, exams/tests/, static/css/
- [ ] T002 [P] Create pinned dependency list in sdd/requirements.txt with Django 5.2 LTS, psycopg[binary], redis, gunicorn, whitenoise
- [ ] T003 [P] Create .env.example and .dockerignore in sdd/ per research.md §8 (DEBUG=False, SECRET_KEY, DJANGO_ALLOWED_HOSTS, POSTGRES_*, VALKEY_*)
- [ ] T004 [P] Create Dockerfile, compose.yaml and entrypoint.sh in sdd/ per research.md §7: db postgres:17-alpine, valkey/valkey:8.0.13-alpine, web gunicorn 2 workers, port 8001, healthchecks

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: конфигурация, модель данных, миграции с ограничениями БД и безопасный доступ к кэшу — блокируют все истории

**⚠️ CRITICAL**: никакие работы по историям не начинаются до завершения этой фазы

- [ ] T005 Create config/settings.py in config/settings.py: DEBUG from env, SECRET_KEY/ALLOWED_HOSTS from .env, PostgreSQL 17, RedisCache with LOCATION from VALKEY_*, whitenoise, LANGUAGE_CODE="ru-RU", USE_TZ, auth, STATIC_ROOT, LOGGING for exams.cache
- [ ] T006 [P] Create manage.py, config/urls.py, config/wsgi.py, exams/__init__.py and exams/apps.py in sdd/
- [ ] T007 Create Topic, Question and AnswerOption models in exams/models.py with database constraints per data-model.md: Topic.slug unique, Topic.title CharField(200) non-empty, Topic.description TextField non-empty, Topic.created_at auto_now_add, Question.topic ForeignKey CASCADE, Question.slug unique within topic, Question.text non-empty, Question.created_at, Question.updated_at, AnswerOption.question ForeignKey CASCADE, AnswerOption.position 1–6 unique per question, AnswerOption.text CharField(255), AnswerOption.is_correct
- [ ] T008 Create Attempt and AttemptAnswer models in exams/models.py with constraints per data-model.md: Attempt.user ForeignKey CASCADE, Attempt.topic ForeignKey SET_NULL null=True, Attempt.topic_id_snapshot, Attempt.topic_title_snapshot CharField(200), Attempt.status choices IN_PROGRESS/COMPLETED, Attempt.started_at, Attempt.completed_at null=True, Attempt.question_count 1–10, Attempt.correct_count 0..question_count, Attempt.percent 0–100, AttemptAnswer.attempt ForeignKey CASCADE, AttemptAnswer.position 1–10 unique per attempt, AttemptAnswer.source_question_id unique per attempt, AttemptAnswer.question_text_snapshot, AttemptAnswer.options_snapshot JSONField, AttemptAnswer.selected_option_key CharField(16) null=True, AttemptAnswer.selected_text_snapshot, AttemptAnswer.correct_option_key CharField(16), AttemptAnswer.correct_text_snapshot, AttemptAnswer.is_correct null=True, AttemptAnswer.answered_at null=True
- [ ] T009 Create exams/migrations/0001_initial.py with UniqueConstraint, CheckConstraint, indexes and status/completed_at invariant from data-model.md (AnswerOption.position, AnswerOption.is_correct, Attempt.question_count, Attempt.correct_count, Attempt.percent, AttemptAnswer.position, AttemptAnswer.source_question_id, AttemptAnswer.is_correct)
- [ ] T010 Create exams/migrations/0002_answer_option_constraints.py with RunSQL: partial unique index on AnswerOption.is_correct and DEFERRABLE INITIALLY DEFERRED trigger enforcing 2–6 options and exactly one correct per data-model.md (AnswerOption.position, AnswerOption.is_correct) per research.md §5
- [ ] T011 Create exams/cache.py with safe_cache_get, safe_cache_set, safe_cache_delete_many and cache-aside helpers for topics:list, leaderboard:topic:<id>, user:best:<user_id>; catch RedisError/OSError with warning in exams.cache; document invalidation strategy next to readers per contracts/cache.md
- [ ] T012 Create exams/signals.py and wire it in exams/apps.py AppConfig.ready() with dispatch_uid: transaction.on_commit(..., robust=True) invalidation for Topic, Question (pre_save old topic_id), AnswerOption and User.username per data-model.md (User.username) and contracts/cache.md
- [ ] T013 [P] Create exams/templates/base.html with lang="ru", Bootstrap 5 CDN and static/css/app.css

**Checkpoint**: основание готово — истории US1–US5 могут реализовываться дальше

---

## Phase 3: User Story 1 — Прохождение теста по теме и разбор результата (Priority: P1) 🎯 MVP

**Goal**: вошедший пользователь проходит тест из до 10 случайных вопросов, отвечает по одному и получает результат с разбором.

**Independent Test**: с демо-данными пройти тест по теме с 12 вопросами: ровно 10 случайных вопросов, «Вопрос N из 10», вопросы по одному, повторный POST не меняет ответ, результат «7 из 10» / «70%» и разбор всех вопросов.

### Tests for User Story 1

> **NOTE**：тесты пишутся первыми и должны УПАСТЬ до реализации

- [ ] T014 [P] [US1] Write exams/tests/test_attempt_flow.py: 10 of 12 random questions, all 6 when fewer, progress indicator, no re-answer via direct POST, result counts/percent/breakdown, 0-question topic

### Implementation for User Story 1

- [ ] T015 [US1] Implement start_attempt(topic, user) in exams/services.py: random order_by("?")[:10], create Attempt and AttemptAnswer snapshots per data-model.md (Attempt.topic_id_snapshot, Attempt.topic_title_snapshot, Attempt.question_count, AttemptAnswer.source_question_id, AttemptAnswer.position, AttemptAnswer.question_text_snapshot, AttemptAnswer.options_snapshot, AttemptAnswer.correct_option_key, AttemptAnswer.correct_text_snapshot)
- [ ] T016 [US1] Implement submit_answer(attempt, option_key) in exams/services.py: conditional update of current unanswered AttemptAnswer filtered by attempt__user; reject re-answer with zero rows; fill AttemptAnswer.selected_option_key, AttemptAnswer.selected_text_snapshot, AttemptAnswer.is_correct, AttemptAnswer.answered_at per data-model.md
- [ ] T017 [US1] Implement complete_attempt(attempt) in exams/services.py: select_for_update(), recount from snapshots, Decimal ROUND_HALF_UP percent, set Attempt.status, Attempt.completed_at, Attempt.correct_count, Attempt.percent per data-model.md; call on_commit cache invalidation for user:best and leaderboard:topic
- [ ] T018 [US1] Create AnswerForm and topic start form in exams/forms.py validating option_key against options_snapshot
- [ ] T019 [US1] Implement attempt_question, attempt_answer and attempt_result views in exams/views.py with get_object_or_404(Attempt, pk=pk, user=request.user) and LoginRequiredMixin
- [ ] T020 [US1] Add attempt routes POST /attempts/start/, GET /attempts/<pk>/question/, POST /attempts/<pk>/answer/, GET /attempts/<pk>/result/ in exams/urls.py
- [ ] T021 [US1] Create exams/templates/exams/attempt_question.html and exams/templates/exams/attempt_result.html with Russian progress indicator and per-question breakdown

**Checkpoint**: US1 полностью функциональна и проверяема отдельно

---

## Phase 4: User Story 2 — Регистрация, вход и список тем (Priority: P2)

**Goal**: посетитель регистрируется, входит и видит список демо-тем с описаниями и количеством вопросов.

**Independent Test**: зарегистрировать пользователя, войти, увидеть 3 темы по 12 вопросов; без входа внутренние страницы перенаправляют на логин; повторная регистрация с тем же именем отклоняется.

### Tests for User Story 2

> **NOTE**：тесты пишутся первыми и должны УПАСТЬ до реализации

- [ ] T022 [P] [US2] Write exams/tests/test_auth_and_topics.py: signup/login/logout redirects, duplicate username and weak password errors, topic list shows 3 demo topics with question_count 12, anonymous access redirect

### Implementation for User Story 2

- [ ] T023 [US2] Wire django.contrib.auth URLs in config/urls.py and implement signup view in exams/views.py with SignUpForm in exams/forms.py using data-model.md (User.username unique, User.password, User.is_active)
- [ ] T024 [P] [US2] Create exams/templates/exams/signup.html, exams/templates/exams/login.html and add auth navigation to exams/templates/base.html with Russian messages
- [ ] T025 [US2] Implement topic_list view in exams/views.py reading topics:list via exams/cache.py helper and annotating question_count=Count("questions")
- [ ] T026 [P] [US2] Create exams/templates/exams/topic_list.html with topic title, description, question_count, empty state and start-test link
- [ ] T027 [US2] Create exams/management/commands/load_demo_data.py in exams/management/commands/: 3 topics × 12 questions via stable slugs and get_or_create inside transaction.atomic(), no overwrite of admin edits, Russian summary per contracts/cli.md

**Checkpoint**: US1 и US2 работают независимо; демо-данные доступны сразу после запуска

---

## Phase 5: User Story 3 — Мои результаты: история попыток и лучшие результаты (Priority: P3)

**Goal**: пользователь видит историю своих завершённых попыток и лучший результат по теме, может открыть свой разбор; чужие попытки недоступны.

**Independent Test**: пройти 2–3 попытки, открыть /results/: history от новых к старым, лучший процент по теме, переход в разбор; прямая ссылка на чужую попытку даёт 404.

### Tests for User Story 3

> **NOTE**：тесты пишутся первыми и должны УПАСТЬ до реализации

- [ ] T028 [P] [US3] Write exams/tests/test_results.py: completed-only history order, best percent per topic, own breakdown link, other user's attempt 404

### Implementation for User Story 3

- [ ] T029 [US3] Add get_user_best cache-aside helper to exams/cache.py grouping completed attempts by data-model.md (Attempt.topic_id_snapshot, Attempt.topic_title_snapshot, Attempt.percent) into user:best:<user_id>
- [ ] T030 [US3] Implement result_list view in exams/views.py: history from DB filtered by user and data-model.md (Attempt.status, Attempt.completed_at) ordered by -completed_at; best results from get_user_best
- [ ] T031 [P] [US3] Create exams/templates/exams/result_list.html with history table, best-results block, empty states and links to /attempts/<pk>/result/ (owner-filtered by view)

**Checkpoint**: US1–US3 функциональны независимо

---

## Phase 6: User Story 4 — Таблица лидеров по теме (Priority: P4)

**Goal**: для темы показывается топ-10 пользователей по личному лучшему проценту; только завершённые попытки.

**Independent Test**: несколько пользователей с разными результатами по одной теме → до 10 строк по убыванию процента, каждый пользователь один раз; пустая тема даёт сообщение «Результатов пока нет».

### Tests for User Story 4

> **NOTE**：тесты пишутся первыми и должны УПАСТЬ до реализации

- [ ] T032 [P] [US4] Write exams/tests/test_leaderboard.py: top-10 limit, one row per user with best percent, deterministic tie order, empty-state message

### Implementation for User Story 4

- [ ] T033 [US4] Implement leaderboard query in exams/services.py: completed attempts only, max data-model.md (Attempt.percent) per user grouped by Attempt.topic_id_snapshot, order by percent desc / Attempt.completed_at asc / data-model.md (User.username) asc, LIMIT 10
- [ ] T034 [US4] Add get_topic_leaderboard cache-aside helper to exams/cache.py for leaderboard:topic:<id> storing plain dicts per contracts/cache.md
- [ ] T035 [US4] Implement leaderboard view in exams/views.py, add route /topics/<topic_id>/leaderboard/ to exams/urls.py and create exams/templates/exams/leaderboard.html with place, username, percent and empty state

**Checkpoint**: все пользовательские истории функциональны независимо

---

## Phase 7: User Story 5 — Управление контентом администратором с сохранением истории (Priority: P5)

**Goal**: администратор управляет темами и вопросами в Django admin; валидация 2–6 вариантов и одного правильного; завершённые попытки не искажаются.

**Independent Test**: завершить попытку, изменить/удалить вопрос администратором, открыть старый разбор — формулировки и результат прежние; новый тест использует обновлённый контент; сохранение вопроса с 1/7 вариантами или без/с двумя правильными отклоняется.

### Tests for User Story 5

> **NOTE**：тесты пишутся первыми и должны УПАСТЬ до реализации

- [ ] T036 [P] [US5] Write exams/tests/test_admin_integrity.py as TransactionTestCase: real commit of deferred trigger rejects 1/7 options, zero/two correct; snapshot immutability after question/topic edits and deletion

### Implementation for User Story 5

- [ ] T037 [US5] Create TopicAdmin, QuestionAdmin and AnswerOptionInline in exams/admin.py, restricting admin to data-model.md (User.is_staff) and stable data-model.md (Topic.slug, Question.slug) fields
- [ ] T038 [US5] Add formset validation in exams/forms.py for data-model.md (AnswerOption.position 1–6 per question, AnswerOption.is_correct exactly one) with Russian error messages before DB write per research.md §5

**Checkpoint**: администрирование и целостность истории работает

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: кэш, деградация Valkey, итоговая проверка по quickstart.md

- [ ] T039 [P] Write exams/tests/test_cache_invalidation.py: prime → change → captureOnCommitCallbacks(execute=True) → fresh value, assertNumQueries(0) on repeat, no invalidation on rollback
- [ ] T040 [P] Write exams/tests/test_cache_fallback.py: mock cache get/set/delete_many to raise redis.exceptions.ConnectionError, assert page served from DB and warning logged in exams.cache
- [ ] T041 Run docker compose exec web python manage.py test in sdd/ and fix all failures across exams/tests/
- [ ] T042 Validate quickstart.md in sdd/: docker compose ps, pg_isready, valkey-cli ping, python manage.py check --deploy, repeated load_demo_data, manual scenario table; verify no SQL on cached reads and Russian UI messages

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: нет зависимостей — можно начинать сразу
- **Foundational (Phase 2)**: зависит от Setup; БЛОКИРУЕТ все истории
- **User Stories (Phase 3–7)**: все зависят от Foundational; further stories depend on earlier ones for shared endpoints (US1 result view reused by US3, topic list from US2 reused by US4)
- **Polish (Phase 8)**: зависит от завершения нужных историй

### User Story Dependencies

- **US1 (P1)**: после Foundational; не зависит от других историй, но предполагает демо-контент из T027 при ручном тесте
- **US2 (P2)**: после Foundational; даёт аутентификацию и список тем, необходимый для Independent Test US1
- **US3 (P3)**: после Foundational и US1 (переиспользует result view)
- **US4 (P4)**: после Foundational и US2 (нужна тема и список тем)
- **US5 (P5)**: после Foundational; независима, но её проверка целостности требует завершённой попытки из US1

### Within Each User Story

- Тесты пишутся первыми и падают до реализации
- Модели (Foundational) → сервисы → формы → представления → URLs → шаблоны
- История считается готовой только после прохождения своего Independent Test

### Parallel Opportunities

- T002, T003, T004 (Setup) — параллельно
- T006, T013 (Foundational) — параллельно с разработкой моделей
- T014, T022, T028, T032, T036, T039, T040 — тесты разных историй параллельно
- T024, T026, T031 — разные шаблоны, параллельно
- Разные истории могут идти параллельно разными разработчиками после Foundational (кроме зависимостей US3→US1, US4→US2)

---

## Parallel Example: User Story 1

```bash
# Тесты US1 (падают до реализации):
Task: "Write exams/tests/test_attempt_flow.py"
# Затем сервисы и представления строго по зависимостям:
Task: "Implement start_attempt(topic, user) in exams/services.py"
Task: "Implement submit_answer(attempt, option_key) in exams/services.py"
Task: "Implement complete_attempt(attempt) in exams/services.py"
# Параллельно после сервисов:
Task: "Create AnswerForm and topic start form in exams/forms.py"
Task: "Create exams/templates/exams/attempt_question.html and exams/templates/exams/attempt_result.html"
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Завершить Phase 1: Setup
2. Завершить Phase 2: Foundational (CRITICAL — блокирует истории)
3. Выполнить T027 (демо-данные) и T022–T026 (вход и список тем) для доступа к US1
4. Выполнить Phase 3: US1
5. **STOP and VALIDATE**: прогнать Independent Test US1 и `python manage.py test`
6. Показать первый рабочий инкремент

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. US2 → регистрация/вход/темы → демо
3. US1 → тест и разбор → MVP
4. US3 → история и лучшие результаты → демо
5. US4 → таблица лидеров → демо
6. US5 → админка и целостность истории → демо
7. Polish → кэш, отказоустойчивость, итоговая проверка

### Parallel Team Strategy

1. Команда вместе закрывает Setup и Foundational
2. После Foundational: разработчик A — US1+US3, разработчик B — US2+US4, разработчик C — US5 и тесты кэша
3. Каждая история интегрируется и проверяется отдельно

---

## Notes

- [P] = разные файлы, нет зависимостей от незавершённых задач
- [Story] обеспечивает трассировку задачи к истории из spec.md
- Ограничения полей не дублируются: каждая такая задача ссылается на `data-model.md` и точное `Entity.field`
- Тесты обязательны (принцип II конституции); перед коммитом все тесты проходят
- Интерфейс и сообщения — на русском; код и имена — на английском (принцип VII)
- Секреты только в `.env`, в git — `.env.example` (принцип III)
- Остановка на любом чекпоинте допустима для независимой проверки истории
