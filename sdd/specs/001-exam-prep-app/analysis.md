# Specification Analysis Report

Проанализированы `spec.md`, `plan.md`, `tasks.md`, `data-model.md`, контракты и `.specify/memory/constitution.md`. Хуки расширений не проверялись: `.specify/extensions.yml` отсутствует. Отчёт пересобран по текущему `tasks.md` (43 задачи: T001–T042 и T044).

Ранее отмеченные блокирующие проблемы устранены: язык описаний задач (CN1), инвалидация bulk/raw (T044), демо-данные и entrypoint перенесены в Foundational (T027), защита всех внутренних страниц задана через `LoginRequiredMiddleware` (T005), валидаторы пароля добавлены в T005, абсолютная формулировка SC-005 смягчена. Ниже — актуальные находки.

## Specification Analysis Report

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| IN1 | Inconsistency | HIGH | tasks.md:201–202, 245, 252–254; spec.md:19 | `tasks.md:201` объявляет US1 независимой от других историй, но `tasks.md:202` и `tasks.md:245` требуют T022–T026 (US2) для Independent Test US1; раздел Incremental Delivery тоже ставит US2 перед US1. | Либо убрать зависимость US1←US2 и создать учётную запись фикстурой в US1, либо явно объявить US2 prerequisite и обновить порядок/нумерацию фаз. |
| IN2 | Inconsistency | HIGH | spec.md:136 (FR-019), 155 (SC-005); contracts/cache.md:30; plan.md:25, 31 | FR-019 и SC-005 требуют «сразу» актуальных данных после изменений, но контракт допускает пропуск инвалидации при недоступном Valkey и устаревший ключ до TTL 300 с после восстановления. В SC-005 оговорка «кэш доступен» есть только для отсутствия SQL, не для свежести. | Добавить «при доступном Valkey» к требованию свежести и зафиксировать поведение при деградации как отдельный измеримый критерий (≤5 мин после восстановления). |
| IN3 | Inconsistency | MEDIUM | data-model.md:30; tasks.md:28; contracts/http.md:30 | `data-model.md` называет `Topic.slug` ключом «демо-данных и URL-ов», тогда как `tasks.md` и HTTP-контракт прямо указывают числовой `<topic_id>` и «не часть URL». | Привести `data-model.md:30` в соответствие с контрактом: slug — ключ демо-данных, маршруты используют `topic_id`. |
| IN4 | Inconsistency | MEDIUM | tasks.md:55 (T011), 182 (T039), 186 (T044), 215–217 | T044 помечен `[P]`, но меняет тот же файл `exams/tests/test_cache_invalidation.py`, что и T039 `[P]`, и использует публичный хелпер инвалидации из T011 (Foundational). Это противоречит определению `[P]` как «разные файлы, нет зависимостей». | Снять `[P]` с T044, добавить явные зависимости T011→T044 и T039→T044 либо объединить работу с хелпером/тестом в T011 и T039. |
| D1 | Duplication | MEDIUM | tasks.md:55 (T011), 186 (T044); contracts/cache.md:45 | Обе задачи создают публичный хелпер инвалидации для прямых записей: T011 («публичный хелпер инвалидации») и T044 («хелпер в exams/cache.py»). | Оставить единственный хелпер в T011; в T044 только подключить его к call-site'ам и тесту. |
| A1 | Ambiguity | MEDIUM | spec.md:109, 165; data-model.md:153–154; contracts/http.md:27; tasks.md:145 (T032), 149 (T033) | При нескольких попытках с одинаковым лучшим `percent` не указано, какой `completed_at` использовать для сортировки лидерборда; «ранее достигнутый результат» не преобразован в конкретную агрегацию. | Зафиксировать `MIN(completed_at)` среди попыток с максимальным `percent` для пары (user, topic_id_snapshot) в spec/data-model/contracts и отразить в T033. |
| U1 | Underspecification | MEDIUM | spec.md:105, 133 (FR-016); data-model.md:147; tasks.md:74 (T014), 123 (T028), 145 (T032), 149 (T033) | Фильтрация `IN_PROGRESS` описана в сервисах и частично в тестах истории, но нет отдельного сценария «прервал → отсутствует в истории/лучших/лидерборде → новая попытка создаётся». | Добавить явный тест-кейс в T014/T028/T032 с проверкой создания новой попытки после `IN_PROGRESS`. |
| D2 | Duplication | LOW | spec.md:136 (FR-019), 155 (SC-005) | FR-019 и SC-005 дублируют требование немедленной актуальности после изменений; различие в измеримости размыто. | Оставить FR-019 правилом, а SC-005 — метрикой со ссылкой на `assertNumQueries(0)` и контрольный сценарий «изменить → открыть». |
| IN5 | Inconsistency | LOW | tasks.md:184–186 | Нумерация задач пропускает ID: после T042 идёт T044, T043 отсутствует. | Переименовать T044→T043 или явно зарезервировать T043, чтобы избежать неоднозначных ссылок. |

**Coverage Summary Table:**

| Requirement Key | Has Task? | Task IDs | Notes |
|-----------------|-----------|----------|-------|
| FR-001 | Да | T022, T023, T024 | Регистрация, уникальное имя, точные сообщения |
| FR-002 | Да | T005, T022, T023, T024 | `LoginRequiredMiddleware` + `login_not_required` + тесты редиректов |
| FR-003 | Да | T011, T025, T026 | Список тем из кэша `topics:list` |
| FR-004 | Да | T014, T015, T018, T019, T020, T021 | Случайная выборка до 10 |
| FR-005 | Да | T014, T019, T021 | Индикатор «Вопрос N из M» |
| FR-006 | Да | T014, T016, T018, T019 | Условное обновление, отказ повторного ответа |
| FR-007 | Да | T014, T017, T019, T021 | Результат и разбор, `ROUND_HALF_UP` |
| FR-008 | Да | T028, T029, T030, T031 | См. U1 по прерванным попыткам |
| FR-009 | Да | T032, T033, T034, T035 | См. A1 по tie-break |
| FR-010 | Да | T019, T028, T031 | Разбор своей попытки |
| FR-011 | Да | T016, T019, T022, T028, T030 | Фильтр по `user=request.user`, 404 на чужую попытку |
| FR-012 | Да | T036, T037, T038 | Создание/редактирование/удаление через admin |
| FR-013 | Да | T007, T009, T010, T036, T038 | Триггер + formset + `CheckConstraint` |
| FR-014 | Да | T008, T015, T016, T017, T036 | Снимки в `AttemptAnswer` |
| FR-015 | Да | T014, T015, T018, T019 | Сообщение «В теме нет вопросов» |
| FR-016 | Да | T008, T014, T028, T030, T032, T033 | Частично: нет явного теста новой попытки (U1) |
| FR-017 | Да | T004, T027, T042 | Entrypoint и демо-данные теперь в Foundational |
| FR-018 | Да | T005, T013, T015, T018, T024, T042 | Русский UI и сообщения |
| FR-019 | Да | T011, T012, T017, T025, T029, T034, T039, T044 | Оговорка по доступности кэша — IN2; качество задачи T044 — IN4/D1 |
| SC-001 | — | — | Исключён из знаменателя: UX-показатель «<5 минут», не инженерная задача |
| SC-002 | Да | T014, T015, T016, T017, T019 | Контрольные прохождения и разбор |
| SC-003 | Да | T019, T022, T028 | Отказ в доступе по прямой ссылке |
| SC-004 | Да | T008, T015, T036 | Сценарий «пройти → изменить → сверить» |
| SC-005 | Да | T011, T012, T017, T025, T029, T034, T039, T040, T042 | Частично: см. IN2 и IN4 |
| SC-006 | Да | T004, T027, T042 | Демо-данные сразу после `docker compose up` |

**Constrained-Field Coverage (when applicable):**

| Field (`Entity.field`) | Canonical Location | Implementing Task IDs | Coverage / Consistency Notes |
|------------------------|--------------------|-----------------------|------------------------------|
| `User.username` | data-model.md:16 | T012, T023, T033 | unique; цитируется явно |
| `User.password` | data-model.md:17, 23 | T023 | Цитируется явно; валидаторы добавлены в T005 |
| `User.is_active` | data-model.md:19 | T023 | Цитируется явно |
| `User.is_staff` | data-model.md:18 | T037 | Цитируется явно |
| `Topic.slug` | data-model.md:30 | T007, T037 | unique; см. IN3 по URL |
| `Topic.title` | data-model.md:31, 39 | T007 | `CharField(200)`, не пустое |
| `Topic.description` | data-model.md:32, 39 | T007 | `TextField`, не пустое |
| `Topic.created_at` | data-model.md:33 | T007 | `auto_now_add` |
| `Question.topic` | data-model.md:46 | T007 | FK `CASCADE` |
| `Question.slug` | data-model.md:47, 54 | T007 | unique в пределах темы |
| `Question.text` | data-model.md:48, 55 | T007 | Не пустое |
| `Question.created_at` / `Question.updated_at` | data-model.md:49 | T007 | `DateTimeField` |
| `AnswerOption.question` | data-model.md:66 | T007 | FK `CASCADE` |
| `AnswerOption.position` | data-model.md:67, 72–73 | T007, T009, T010, T038 | 1–6, unique на вопрос |
| `AnswerOption.text` | data-model.md:68 | T007 | `CharField(255)` |
| `AnswerOption.is_correct` | data-model.md:69, 74–75 | T007, T009, T010, T038 | Ровно один правильный |
| `Attempt.user` | data-model.md:84 | T008 | FK `CASCADE` |
| `Attempt.topic` | data-model.md:85 | T008 | FK `SET_NULL`, `null=True` |
| `Attempt.topic_id_snapshot` | data-model.md:86 | T008, T015, T029, T033 | positive int |
| `Attempt.topic_title_snapshot` | data-model.md:87 | T008, T015, T029 | `CharField(200)` |
| `Attempt.status` | data-model.md:88, 101 | T008, T009, T030, T033 | Choices + инвариант `completed_at` |
| `Attempt.started_at` | data-model.md:89 | T008 | `DateTimeField` |
| `Attempt.completed_at` | data-model.md:90, 101 | T008, T009, T030, T033 | `null` + инвариант статуса; см. A1 |
| `Attempt.question_count` | data-model.md:91, 98 | T008, T009 | 1–10 |
| `Attempt.correct_count` | data-model.md:92, 99 | T008, T009 | 0..question_count |
| `Attempt.percent` | data-model.md:93, 100 | T008, T009, T033 | 0–100, округление |
| `AttemptAnswer.attempt` | data-model.md:111 | T008 | FK `CASCADE` |
| `AttemptAnswer.position` | data-model.md:112, 124, 126 | T008, T009 | 1–10, unique на попытку |
| `AttemptAnswer.source_question_id` | data-model.md:113, 125 | T008, T009, T015 | unique на попытку |
| `AttemptAnswer.question_text_snapshot` | data-model.md:114 | T008, T015 | Снимок формулировки |
| `AttemptAnswer.options_snapshot` | data-model.md:115 | T008, T015, T016, T018 | `JSONField` со схемой key/text |
| `AttemptAnswer.selected_option_key` | data-model.md:116 | T008, T016 | `CharField(16)`, `null=True` |
| `AttemptAnswer.selected_text_snapshot` | data-model.md:117 | T008, T016 | `TextField(blank=True)` |
| `AttemptAnswer.correct_option_key` | data-model.md:118 | T008, T015 | `CharField(16)`, `blank=True` |
| `AttemptAnswer.correct_text_snapshot` | data-model.md:119 | T008, T015 | `TextField(blank=True)` |
| `AttemptAnswer.is_correct` | data-model.md:120, 127 | T008, T009, T016 | `null=True`, не без ответа |
| `AttemptAnswer.answered_at` | data-model.md:121 | T008, T016 | `null=True` |

Неразрешённых ссылок на поля и прямых противоречий между ограничениями `data-model.md` и формулировками задач не обнаружено. Замечания IN4/D1 касаются организации задачи T044, а не цитирований полей.

**Constitution Alignment Issues:**

- CRITICAL-нарушений нет: принцип VII соблюдён после перевода описаний задач, принцип III — после добавления `LoginRequiredMiddleware` и валидаторов пароля, принцип VI — после добавления T044.
- Качество реализации принципа VI уточнено в IN4 и D1 (дублирование хелпера и некорректный `[P]` у T044).
- Принципы I, II, IV, V отражены в плане и задачах без нарушений.

**Unmapped Tasks:**

| Task ID | Техническое соответствие |
|---------|--------------------------|
| T001, T002, T003, T006 | Каркас проекта, зависимости, точки входа, секреты — constitution I, III, V |
| T041 | Прогон всех тестов — constitution II |

Эти задачи не являются пропуском покрытия FR/SC: они реализуют архитектурные и качественные ограничения плана и конституции.

**Metrics:**

- Total Requirements: 24 (19 FR + 5 SC, требующих реализуемой работы; SC-001 исключён как пост-релизный UX-показатель)
- Total Tasks: 43 (T001–T042 и T044; см. IN5)
- Coverage % (requirements with >=1 task): 100% (24/24; качество покрытия уточнено в IN1, IN2, IN4, U1)
- Ambiguity Count: 1
- Duplication Count: 2
- Critical Issues Count: 0

## Next Actions

- CRITICAL-проблем нет; перед `/speckit.implement` рекомендуется закрыть HIGH-находки IN1 (зависимость US1/US2) и IN2 (свежесть при недоступном Valkey).
- Для IN2: `Run /speckit.specify with refinement` — уточнить FR-019/SC-005 и synchronized-оговорку в `contracts/cache.md`.
- Для IN1 и IN4/D1/IN5: вручную отредактировать `tasks.md` — уточнить зависимости, снять `[P]` с T044, устранить дубль хелпера и пропуск T043; затем `Run /speckit.tasks` для пересборки связей.
- Для A1 и U1: уточнить правило tie-break в `data-model.md`/`contracts/http.md` и добавить тест прерванной попытки в T014/T028/T032.
- LOW-находки D2 и IN5 можно устранить попутно без блокировки реализации.

Хотите, чтобы я предложил конкретные правки для топ-N проблем? Правки не будут применены без вашего явного подтверждения.
