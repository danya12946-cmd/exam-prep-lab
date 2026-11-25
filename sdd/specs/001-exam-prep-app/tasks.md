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
- Маршруты тем используют числовой `<topic_id>`; `Topic.slug` — стабильный ключ демо-данных, не часть URL (см. `contracts/http.md`)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: воспроизводимый каркас проекта по `plan.md` и `research.md`

- [X] T001 Создать структуру проекта в sdd/ по plan.md: config/, exams/migrations/, exams/management/commands/, exams/templates/exams/, exams/tests/, static/css/
- [X] T002 [P] Создать зафиксированный список зависимостей в sdd/requirements.txt: Django 5.2 LTS, psycopg[binary], redis, gunicorn, whitenoise
- [X] T003 [P] Создать .env.example и .dockerignore в sdd/ по research.md §8 (DEBUG=False, SECRET_KEY, DJANGO_ALLOWED_HOSTS, POSTGRES_*, VALKEY_*)
- [X] T004 [P] Создать Dockerfile и compose.yaml в sdd/ по research.md §7: db postgres:17-alpine, valkey/valkey:8.0.13-alpine, web gunicorn 2 workers, port 8001, healthchecks; entrypoint.sh создаётся в T027

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: конфигурация, модель данных, миграции с ограничениями БД и безопасный доступ к кэшу — блокируют все истории

**⚠️ CRITICAL**: никакие работы по историям не начинаются до завершения этой фазы

- [X] T005 Создать config/settings.py: DEBUG из окружения, SECRET_KEY/ALLOWED_HOSTS из .env, PostgreSQL 17, RedisCache с LOCATION из VALKEY_*, whitenoise, LANGUAGE_CODE="ru-RU", USE_TZ, auth, STATIC_ROOT, LOGGING для exams.cache, AUTH_PASSWORD_VALIDATORS; подключить django.contrib.auth.middleware.LoginRequiredMiddleware сразу после AuthenticationMiddleware; LOGIN_URL="/accounts/login/" (login и signup помечаются login_not_required в T023)
- [X] T006 [P] Создать manage.py, config/urls.py, config/wsgi.py, exams/__init__.py и exams/apps.py в sdd/
- [X] T007 Создать модели Topic, Question и AnswerOption в exams/models.py с ограничениями БД по data-model.md: Topic.slug unique, Topic.title CharField(200) не пустое, Topic.description TextField не пустое, Topic.created_at auto_now_add, Question.topic ForeignKey CASCADE, Question.slug unique в пределах темы, Question.text не пустое, Question.created_at, Question.updated_at, AnswerOption.question ForeignKey CASCADE, AnswerOption.position 1–6 unique на вопрос, AnswerOption.text CharField(255), AnswerOption.is_correct
- [X] T008 Создать модели Attempt и AttemptAnswer в exams/models.py с ограничениями по data-model.md: Attempt.user ForeignKey CASCADE, Attempt.topic ForeignKey SET_NULL null=True, Attempt.topic_id_snapshot, Attempt.topic_title_snapshot CharField(200), Attempt.status choices IN_PROGRESS/COMPLETED, Attempt.started_at, Attempt.completed_at null=True, Attempt.question_count 1–10, Attempt.correct_count 0..question_count, Attempt.percent 0–100, AttemptAnswer.attempt ForeignKey CASCADE, AttemptAnswer.position 1–10 unique на попытку, AttemptAnswer.source_question_id unique на попытку, AttemptAnswer.question_text_snapshot, AttemptAnswer.options_snapshot JSONField, AttemptAnswer.selected_option_key CharField(16) null=True, AttemptAnswer.selected_text_snapshot, AttemptAnswer.correct_option_key CharField(16), AttemptAnswer.correct_text_snapshot, AttemptAnswer.is_correct null=True, AttemptAnswer.answered_at null=True
- [X] T009 Создать exams/migrations/0001_initial.py с UniqueConstraint, CheckConstraint, индексами и инвариантом status/completed_at по data-model.md (AnswerOption.position, AnswerOption.is_correct, Attempt.question_count, Attempt.correct_count, Attempt.percent, AttemptAnswer.position, AttemptAnswer.source_question_id, AttemptAnswer.is_correct)
- [X] T010 Создать exams/migrations/0002_answer_option_constraints.py (SQL внутри миграции через RunSQL, отдельного .sql файла нет) с partial unique index на AnswerOption.is_correct и DEFERRABLE INITIALLY DEFERRED trigger, обеспечивающим 2–6 вариантов и ровно один правильный по data-model.md (AnswerOption.position, AnswerOption.is_correct) по research.md §5
- [X] T011 Создать exams/cache.py с safe_cache_get, safe_cache_set, safe_cache_delete_many и cache-aside хелперами для topics:list, leaderboard:topic:<id>, user:best:<user_id>; перехватывать RedisError/OSError с предупреждением в exams.cache; описать стратегию инвалидации рядом с хелперами чтения; реализовать единственный публичный хелпер инвалидации для прямых записей (QuerySet.update(), bulk_create(), bulk_update(), raw SQL) по contracts/cache.md:45
- [X] T012 Создать exams/signals.py и подключить его в exams/apps.py AppConfig.ready() с dispatch_uid: инвалидация через transaction.on_commit(..., robust=True) для Topic, Question (pre_save старый topic_id), AnswerOption и User.username по data-model.md (User.username) и contracts/cache.md
- [X] T027 Создать exams/management/commands/load_demo_data.py в exams/management/commands/: 3 темы × 12 вопросов через стабильные slug и get_or_create внутри transaction.atomic(), без перезаписи правок администратора, русский итог по contracts/cli.md; создать entrypoint.sh в sdd/ с collectstatic --noinput, migrate --noinput, load_demo_data и gunicorn на 0.0.0.0:8000 с 2 worker по research.md §7
- [X] T013 [P] Создать exams/templates/base.html с lang="ru", Bootstrap 5 CDN и static/css/app.css

**Checkpoint**: основание готово — истории US1–US5 могут реализовываться дальше; демо-данные и entrypoint готовы

---

## Phase 3: User Story 2 — Регистрация, вход и список тем (Priority: P2)

**Goal**: посетитель регистрируется, входит и видит список демо-тем с описаниями и количеством вопросов.

**Independent Test**: зарегистрировать пользователя, войти, увидеть 3 темы по 12 вопросов; без входа внутренние страницы перенаправляют на логин; повторная регистрация с тем же именем отклоняется.

### Tests for User Story 2

> **NOTE**：тесты пишутся первыми и должны УПАСТЬ до реализации

- [X] T022 [P] [US2] Написать exams/tests/test_auth_and_topics.py: редиректы signup/login/logout, ошибки занятого имени и простого пароля, список тем показывает 3 демо-темы с question_count 12, редирект для анонима; проверить, что анонимный запрос к внутренним страницам (/results/, /topics/<topic_id>/leaderboard/, /attempts/<pk>/question/) перенаправляется на /accounts/login/; проверить точные сообщения из contracts/http.md: "Имя пользователя уже занято", "Пароль не может быть пустым", "Пароль слишком простой", "Пароли не совпадают", "Неверное имя пользователя или пароль"

### Implementation for User Story 2

- [X] T023 [US2] Подключить URL django.contrib.auth в config/urls.py (только login/logout; LogoutView принимает POST) и добавить явный path("accounts/signup/", signup, name="signup"), так как в auth.urls нет маршрута signup; реализовать представление signup в exams/views.py с SignUpForm в exams/forms.py, используя data-model.md (User.username unique, User.password, User.is_active), и выводить ошибки формы с точными текстами из contracts/http.md; пометить представление signup декоратором login_not_required (стандартный LoginView уже помечен этим декоратором в Django 5.2)
- [X] T024 [P] [US2] Создать exams/templates/exams/signup.html, exams/templates/exams/login.html и добавить навигацию авторизации в exams/templates/base.html с русскими сообщениями; отображать ошибки формы и django.contrib.messages с точными текстами из contracts/http.md
- [X] T025 [US2] Реализовать представление topic_list в exams/views.py, читающее topics:list через хелпер exams/cache.py и аннотирующее question_count=Count("questions")
- [X] T026 [P] [US2] Создать exams/templates/exams/topic_list.html с названием темы, описанием, question_count, пустым состоянием и ссылкой начала теста

**Checkpoint**: US2 готова; демо-данные доступны сразу после запуска; prerequisite US1 выполнен

---

## Phase 4: User Story 1 — Прохождение теста по теме и разбор результата (Priority: P1) 🎯 MVP

**Prerequisite**: US2 (учётная запись, вход и список тем)

**Goal**: вошедший пользователь проходит тест из до 10 случайных вопросов, отвечает по одному и получает результат с разбором.

**Independent Test**: с учётной записью из US2 и демо-данными пройти тест по теме с 12 вопросами: ровно 10 случайных вопросов, «Вопрос N из 10», вопросы по одному, повторный POST не меняет ответ, результат «7 из 10» / «70%» и разбор всех вопросов.

### Tests for User Story 1

> **NOTE**：тесты пишутся первыми и должны УПАСТЬ до реализации

- [X] T014 [P] [US1] Написать exams/tests/test_attempt_flow.py: 10 из 12 случайных вопросов, все 6 если вопросов меньше, индикатор прогресса, отказ повторного ответа прямым POST, количество/процент/разбор результата, тема с 0 вопросов; отдельный тест прерванной попытки: после незавершённой `IN_PROGRESS` можно начать новую попытку по теме

### Implementation for User Story 1

- [X] T015 [US1] Реализовать start_attempt(topic, user) в exams/services.py: случайный order_by("?")[:10], создание снимков Attempt и AttemptAnswer по data-model.md (Attempt.topic_id_snapshot, Attempt.topic_title_snapshot, Attempt.question_count, AttemptAnswer.source_question_id, AttemptAnswer.position, AttemptAnswer.question_text_snapshot, AttemptAnswer.options_snapshot, AttemptAnswer.correct_option_key, AttemptAnswer.correct_text_snapshot); если в теме нет вопросов — ничего не создавать и вернуть ошибку с русским сообщением "В теме нет вопросов" по contracts/http.md
- [X] T016 [US1] Реализовать submit_answer(attempt, option_key) в exams/services.py: условное обновление текущего неотвеченного AttemptAnswer с фильтром attempt__user; отклонять повторный ответ при нуле обновлённых строк и возвращать "Ответ уже сохранён"; не принимать ключ, отсутствующий в AttemptAnswer.options_snapshot, и возвращать "Выберите один из предложенных вариантов"; заполнить AttemptAnswer.selected_option_key, AttemptAnswer.selected_text_snapshot, AttemptAnswer.is_correct, AttemptAnswer.answered_at по data-model.md; на последнем ответе вызвать complete_attempt(attempt) (T017) в том же запросе по contracts/http.md
- [X] T017 [US1] Реализовать complete_attempt(attempt) в exams/services.py: select_for_update(), пересчёт по снимкам, процент Decimal ROUND_HALF_UP, установить Attempt.status, Attempt.completed_at, Attempt.correct_count, Attempt.percent по data-model.md; вызвать инвалидацию кэша через on_commit для user:best и leaderboard:topic
- [X] T018 [US1] Создать AnswerForm и форму начала теста в exams/forms.py с валидацией option_key против AttemptAnswer.options_snapshot и ошибкой "Выберите один из предложенных вариантов"; проверять, что тема существует и содержит вопросы, с ошибками "Тема не найдена" и "В теме нет вопросов" по contracts/http.md
- [X] T019 [US1] Реализовать представления attempt_question, attempt_answer и attempt_result в exams/views.py с get_object_or_404(Attempt, pk=pk, user=request.user); при отсутствии или пустоте темы перенаправлять на / с сообщениями из T018 и не создавать Attempt; при невалидном option_key перепоказывать текущий вопрос; при повторном ответе показывать "Ответ уже сохранён" без изменения данных
- [X] T020 [US1] Добавить маршруты POST /attempts/start/, GET /attempts/<pk>/question/, POST /attempts/<pk>/answer/, GET /attempts/<pk>/result/ в exams/urls.py
- [X] T021 [US1] Создать exams/templates/exams/attempt_question.html и exams/templates/exams/attempt_result.html с русским индикатором прогресса и разбором по каждому вопросу

**Checkpoint**: US1 полностью функциональна и проверяема отдельно после завершения US2

---

## Phase 5: User Story 3 — Мои результаты: история попыток и лучшие результаты (Priority: P3)

**Goal**: пользователь видит историю своих завершённых попыток и лучший результат по теме, может открыть свой разбор; чужие попытки недоступны.

**Independent Test**: пройти 2–3 попытки, открыть /results/: history от новых к старым, лучший процент по теме, переход в разбор; прямая ссылка на чужую попытку даёт 404.

### Tests for User Story 3

> **NOTE**：тесты пишутся первыми и должны УПАСТЬ до реализации

- [X] T028 [P] [US3] Написать exams/tests/test_results.py: порядок истории только завершённых попыток, лучший процент по теме, ссылка на свой разбор, 404 на чужую попытку; отдельный тест прерванной попытки: статус `IN_PROGRESS` отсутствует в истории и лучших результатах, а новая попытка по теме создаётся после прерывания

### Implementation for User Story 3

- [X] T029 [US3] Добавить cache-aside хелпер get_user_best в exams/cache.py, группирующий завершённые попытки по data-model.md (Attempt.topic_id_snapshot, Attempt.topic_title_snapshot, Attempt.percent) в user:best:<user_id>; при нескольких попытках с одинаковым максимальным percent брать MIN(Attempt.completed_at)
- [X] T030 [US3] Реализовать представление result_list в exams/views.py: история из БД с фильтром по пользователю и data-model.md (Attempt.status, Attempt.completed_at) в порядке -completed_at; лучшие результаты из get_user_best
- [X] T031 [P] [US3] Создать exams/templates/exams/result_list.html с таблицей истории, блоком лучших результатов, пустыми состояниями и ссылками на /attempts/<pk>/result/ (фильтр по владельцу в представлении)

**Checkpoint**: US1–US3 функциональны независимо

---

## Phase 6: User Story 4 — Таблица лидеров по теме (Priority: P4)

**Goal**: для темы показывается топ-10 пользователей по личному лучшему проценту; только завершённые попытки.

**Independent Test**: несколько пользователей с разными результатами по одной теме → до 10 строк по убыванию процента, каждый пользователь один раз; пустая тема даёт сообщение «Результатов пока нет».

### Tests for User Story 4

> **NOTE**：тесты пишутся первыми и должны УПАСТЬ до реализации

- [X] T032 [P] [US4] Написать exams/tests/test_leaderboard.py: лимит топ-10, одна строка на пользователя с лучшим процентом, детерминированный порядок при равенстве (MIN(completed_at) среди попыток с максимальным percent для пары (user, topic_id_snapshot), затем User.username asc по contracts/http.md), сообщение пустого состояния "Результатов пока нет"; отдельный тест прерванной попытки: незавершённая `IN_PROGRESS` отсутствует в лидерборде, а новая попытка по теме создаётся и учитывается

### Implementation for User Story 4

- [X] T033 [US4] Реализовать запрос лидерборда в exams/services.py: только завершённые попытки, максимум data-model.md (Attempt.percent) на пользователя, сгруппировано по Attempt.topic_id_snapshot, при равенстве процентов брать MIN(Attempt.completed_at) среди попыток с максимальным percent для пары (user, topic_id_snapshot), сортировка percent desc / completed_at asc / data-model.md (User.username) asc, LIMIT 10; порядок при равенстве соответствует contracts/http.md
- [X] T034 [US4] Добавить cache-aside хелпер get_topic_leaderboard в exams/cache.py для leaderboard:topic:<id> с хранением простых dict по contracts/cache.md
- [X] T035 [US4] Реализовать представление leaderboard в exams/views.py, добавить маршрут /topics/<topic_id>/leaderboard/ в exams/urls.py и создать exams/templates/exams/leaderboard.html с местом, username, процентом и пустым состоянием

**Checkpoint**: все пользовательские истории функциональны независимо

---

## Phase 7: User Story 5 — Управление контентом администратором с сохранением истории (Priority: P5)

**Goal**: администратор управляет темами и вопросами в Django admin; валидация 2–6 вариантов и одного правильного; завершённые попытки не искажаются.

**Independent Test**: завершить попытку, изменить/удалить вопрос администратором, открыть старый разбор — формулировки и результат прежние; новый тест использует обновлённый контент; сохранение вопроса с 1/7 вариантами или без/с двумя правильными отклоняется.

### Tests for User Story 5

> **NOTE**：тесты пишутся первыми и должны УПАСТЬ до реализации

- [ ] T036 [P] [US5] Написать exams/tests/test_admin_integrity.py как TransactionTestCase: реальный commit отложенного trigger отвергает 1/7 вариантов, ноль/два правильных; неизменяемость снимков после правок и удаления вопроса/темы

### Implementation for User Story 5

- [ ] T037 [US5] Создать TopicAdmin, QuestionAdmin и AnswerOptionInline в exams/admin.py, ограничив доступ по data-model.md (User.is_staff) и стабильные поля data-model.md (Topic.slug, Question.slug)
- [ ] T038 [US5] Добавить валидацию formset в exams/forms.py для data-model.md (AnswerOption.position 1–6 на вопрос, AnswerOption.is_correct ровно один) с русскими сообщениями об ошибках до записи в БД по research.md §5

**Checkpoint**: администрирование и целостность истории работает

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: кэш, деградация Valkey, итоговая проверка по quickstart.md

- [ ] T039 [P] Написать exams/tests/test_cache_invalidation.py: prime → изменение → captureOnCommitCallbacks(execute=True) → новое значение, assertNumQueries(0) при повторном чтении, отсутствие инвалидации при rollback
- [ ] T040 [P] Написать exams/tests/test_cache_fallback.py: подменить cache get/set/delete_many так, чтобы они выбрасывали redis.exceptions.ConnectionError; проверить, что страница отдаётся из БД и в лог exams.cache пишется предупреждение
- [ ] T041 Запустить docker compose exec web python manage.py test в sdd/ и исправить все падения в exams/tests/
- [ ] T042 Проверить quickstart.md в sdd/: docker compose ps, pg_isready, valkey-cli ping, python manage.py check --deploy, повторный load_demo_data, таблица ручных сценариев; убедиться, что нет SQL при чтении из кэша и что сообщения интерфейса на русском
- [ ] T043 Зависит от T011 и T039. Добавить явную инвалидацию кэша для QuerySet.update(), bulk_create(), bulk_update() и raw SQL по contracts/cache.md:45: подключить публичный хелпер из T011 во всех таких местах и проверить его в exams/tests/test_cache_invalidation.py (файл создаётся в T039)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: нет зависимостей — можно начинать сразу
- **Foundational (Phase 2)**: зависит от Setup; БЛОКИРУЕТ все истории
- **User Stories (Phase 3–7)**: все зависят от Foundational; порядок историй: US2 → US1 → US3 → US4 → US5; последующие истории зависят от предыдущих из-за общих точек входа и prerequisite (US1 требует US2, US3 переиспользует result view из US1, US4 использует список тем из US2)
- **Polish (Phase 8)**: зависит от завершения нужных историй

### User Story Dependencies

- **US2 (P2)**: после Foundational; даёт аутентификацию и список тем; prerequisite для US1
- **US1 (P1)**: после Foundational и US2; демо-контент и entrypoint создаются в T027 (Foundational), учётная запись и вход — в US2
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
- T022, T028, T032, T036, T039, T040 — тесты разных историй параллельно; T014 — после завершения US2
- T024, T026, T031 — разные шаблоны, параллельно
- Разные истории могут идти параллельно разными разработчиками после Foundational (кроме зависимостей US1→US2, US3→US1, US4→US2)

---

## Parallel Example: User Story 1

Prerequisite: US2 завершена.

```bash
# Тесты US1 (падают до реализации):
Task: "Написать exams/tests/test_attempt_flow.py"
# Затем сервисы и представления строго по зависимостям:
Task: "Реализовать start_attempt(topic, user) в exams/services.py"
Task: "Реализовать submit_answer(attempt, option_key) в exams/services.py"
Task: "Реализовать complete_attempt(attempt) в exams/services.py"
# Параллельно после сервисов:
Task: "Создать AnswerForm и форму начала теста в exams/forms.py"
Task: "Создать exams/templates/exams/attempt_question.html и exams/templates/exams/attempt_result.html"
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Завершить Phase 1: Setup
2. Завершить Phase 2: Foundational (CRITICAL — блокирует истории)
3. Выполнить Phase 3: US2 (T022–T026; демо-данные уже созданы в T027)
4. Выполнить Phase 4: US1 (prerequisite — US2)
5. **STOP and VALIDATE**: прогнать Independent Test US1 и `python manage.py test`
6. Показать первый рабочий инкремент

### Incremental Delivery

1. Setup + Foundational → основание готово
2. US2 → регистрация/вход/темы → демо
3. US1 → тест и разбор → MVP
4. US3 → история и лучшие результаты → демо
5. US4 → таблица лидеров → демо
6. US5 → админка и целостность истории → демо
7. Polish → кэш, отказоустойчивость, итоговая проверка

### Parallel Team Strategy

1. Команда вместе закрывает Setup и Foundational
2. После Foundational: разработчик A — US2+US4, разработчик B — US1+US3 (после US2), разработчик C — US5 и тесты кэша
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
