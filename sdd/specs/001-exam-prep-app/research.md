# Исследование: веб-приложение для подготовки к экзамену

**Дата**: 2026-11-23  
**Связанные документы**: `spec.md`, `plan.md`, `.specify/memory/constitution.md`

Цель Phase 0 — зафиксировать технические решения до проектирования моделей и контрактов. Неопределённостей (`NEEDS CLARIFICATION`) нет: стек и ключевые архитектурные решения заданы пользователем, функциональные требования — spec.md. Актуальная документация проверена через context7: Django 5.2.18 (`/django/django/5.2.18`) и Valkey 8.0.13 (`/valkey-io/valkey-doc/8.0.13`).

## 1. Язык, стек и структура проекта

**Decision**: Python 3.12, Django 5.2 LTS, один монолит с единственным приложением `exams` в корне `sdd/`. Хранилище — PostgreSQL 17, кэш — Valkey 8. Веб-сервер — gunicorn, статика — whitenoise, интерфейс — Django templates + Bootstrap 5 через CDN.

**Rationale**: это точно соответствует вводным пользователя и принципам I/V конституции: один процесс Django, минимальное число зависимостей, одинаковый запуск в разработке и на проверке. Bootstrap через CDN не добавляет node/npm-сборку; whitenoise остаётся только для собственной статики.

**Alternatives considered**: несколько Django-приложений или отдельный SPA-фронтенд — лишние слои для учебной нагрузки; локальная npm-сборка Bootstrap — новый toolchain; SQLite — не соответствует стеку; nginx-sidecar — лишний сервис сверх PostgreSQL и Valkey.

## 2. Кэш Django → Valkey

**Decision**: использовать штатный бэкенд `django.core.cache.backends.redis.RedisCache` с `LOCATION`, собранным из переменных окружения `VALKEY_HOST`, `VALKEY_PORT`, `VALKEY_DB`, `VALKEY_PASSWORD` в формате `redis://...`. Кэшировать три набора: `topics:list`, `leaderboard:topic:<id>`, `user:best:<user_id>`. Чтение — через хелперы в `exams/cache.py` по шаблону `get` → база → `set` (эквивалент `get_or_set`); в кэше только простые `dict`/`list`, никогда QuerySet. Для тестов — `LocMemCache` через `@override_settings`. Все обращения к кэшу идут через безопасные обёртки `safe_cache_get/set/delete_many`: Valkey считается только ускорением, база — источником истины.

**Rationale**: документация Django задаёт именно `BACKEND=django.core.cache.backends.redis.RedisCache` и URL `redis://host:port/db`. Valkey использует RESP; по документации Valkey клиенты общаются с сервером через REdis Serialization Protocol (RESP), а `PING` возвращает `PONG`, поэтому стандартный Redis-клиент Django совместим с Valkey 8 на RESP2. Общий кэш нужен всем воркерам gunicorn; `LocMemCache` в проде дал бы рассинхрон между процессами.

**Отказоустойчивость**: обёртки перехватывают `redis.exceptions.RedisError` (базовый класс для `ConnectionError` и `TimeoutError` в redis-py, см. документацию v5.2) и `OSError`, пишут `logger.warning(..., exc_info=True)` в лог `exams.cache` и возвращают sentinel для чтения или no-op для записи и инвалидации. Исключение не доходит до view: при недоступном Valkey страница строится из PostgreSQL. Общий `Exception` не ловится, чтобы не маскировать программные ошибки. Пока кэш недоступен, инвалидации пропускаются; после восстановления TTL (300 с) ограничивает время жизни возможно устаревшего ключа, а конфигурация Valkey без persistence означает, что после перезапуска кэш пуст.

**Alternatives considered**: `django-redis` ради `delete_pattern()` — лишняя зависимость, штатный API имеет `get/set/delete/delete_many`; `cache_page` — кэширует HTML целиком и плохо управляется вручную; `functools.lru_cache` — изолирован в процессе; кэширование чужих попыток — опасно для FR-011; проброс ошибок Valkey в view — роняет приложение при недоступности кэша; in-memory fallback — рассинхрон между воркерами; circuit breaker — лишняя зависимость для учебной нагрузки.

Питфоллы: у `RedisCache` нет `delete_pattern()`; пустой список нужно отличать от промаха (sentinel); пароль в URL экранируется; `cache.clear()` делает `FLUSHDB`, поэтому кэш приложения держится в отдельной DB; TTL — страховка, а не замена инвалидации. Стратегия инвалидации фиксируется комментариями рядом с хелперами чтения, как требует принцип VI.

## 3. Инвалидация кэша

**Decision**: подключить сигналы в `AppConfig.ready()` с `dispatch_uid`. `post_save`/`post_delete` для `Topic`, `Question`, `AnswerOption` и `User` (только при смене `username`) инициируют `transaction.on_commit(partial(invalidate, ...), using=using, robust=True)`. Карта инвалидации:
- `Topic` → `topics:list`; при удалении также `leaderboard:topic:<id>`.
- `Question` → `topics:list` старого и нового `topic_id` (старый сохраняется в `pre_save`).
- `AnswerOption` → `topics:list` вопроса.
- `User.username` → все `leaderboard:topic:*` (имена хранятся в кэше).
- Завершение попытки в `services.complete_attempt()` → `user:best:<user_id>` и `leaderboard:topic:<topic_id>`.

Прямые массовые/raw-записи обязаны явно вызывать те же функции инвалидации; такие места перечисляются в `cache.py`.

**Rationale**: документация Django указывает, что `transaction.on_commit` выполняется только после успешного commit и отбрасывается при rollback. Инвалидация внутри транзакции создаёт гонку: другой запрос может наполнить кэш старыми данными до commit. `robust=True` не даёт ошибке Valkey сорвать уже закоммиченный пользовательский запрос; дополнительно `delete_many` вызывается через ту же безопасную обёртку, поэтому при недоступности кэша инвалидация пропускается и логируется, а транзакция БД остаётся успешной. Точные keys дешевле и предсказуемее, чем сканирование ключей.

**Alternatives considered**: `cache.clear()` на каждое изменение — стирает чужие данные и сессии; TTL-only — нарушает FR-019; глобальный bump `VERSION` — инвалидирует всё без нужды; PostgreSQL `NOTIFY`/триггер на инвалидацию — надёжнее для raw SQL, но слишком сложно для учебного проекта и не требуется при явном запрете обходить сервисный слой.

Питфоллы: `TestCase` не коммитит транзакцию, поэтому тесты инвалидации используют `captureOnCommitCallbacks(execute=True)`; это не заменяет тест отложенного trigger с реальным commit (см. разделы 5–6); `QuerySet.update()`/`bulk_create()`/`bulk_update()` не шлют `post_save`.

## 4. Состояние попытки и неизменяемая история

**Decision**: `Attempt` хранится в базе со статусом `IN_PROGRESS`/`COMPLETED`. В начале теста сервис создаёт `Attempt` и `AttemptAnswer` со снимками вопросов и вариантов (`order_by("?")[:10]`). Ответ записывается условным `UPDATE ... WHERE selected_option_id IS NULL AND attempt__user=request.user`; ноль обновлённых строк означает повторный ответ и отклоняется. Завершение делает `select_for_update()`, считает результат только по снимкам и округляет процент через `Decimal.quantize(..., ROUND_HALF_UP)`. Разбор читает только `AttemptAnswer`, не живые `Question`/`AnswerOption`.

**Rationale**: это одновременно выполняет FR-006, FR-011 и FR-014: повторный ответ невозможен даже прямым POST, чужая попытка не доступна фильтрацией по пользователю, а правки/удаление контента администратором не влияют на старую попытку. `ForeignKey(topic, on_delete=SET_NULL, null=True)` + `topic_title_snapshot` сохраняют историю даже при удалении темы. Встроенный `round()` Python использует банковское округление, поэтому для «математического» правила из spec нужен `Decimal`.

**Alternatives considered**: хранить текущий вопрос в сессии — состояние теряется и плохо проверяется; ссылаться на живые вопросы из попытки — история искажается; хранить всю попытку как один JSON без ограничений — слабая целостность; продолжать прерванную попытку — исключено assumptions spec.md.

## 5. Ограничения базы данных и админка

**Decision**: живые модели получают `UniqueConstraint`, `CheckConstraint` и `ForeignKey` в миграциях. Для правил «от 2 до 6 вариантов» и «ровно один правильный» используется отложенный (`DEFERRABLE INITIALLY DEFERRED`) PostgreSQL constraint trigger, созданный через `RunSQL`, поскольку `CheckConstraint` не видит количество связанных строк. Django admin использует inline formset с русскими сообщениями как UX-слой поверх тех же правил.

**Rationale**: принцип IV требует, чтобы целостность гарантировалась базой; отложенный trigger позволяет formset'у временно снять и заново поставить флаг правильности в рамках одной транзакции. Partial unique index на `is_correct=True` дополнительно защищает от гонки двух правильных вариантов.

**Тестирование trigger**: `TestCase` держит транзакцию открытой и откатывает её, поэтому `DEFERRABLE INITIALLY DEFERRED` не проверяется и тест может ложно пройти. Тесты `test_admin_integrity.py` наследуют `TransactionTestCase`; некорректная запись выполняется внутри `transaction.atomic()`, а `IntegrityError` ожидается при выходе из блока, когда PostgreSQL действительно проверяет ограничение. Остальные тесты остаются на `TestCase`.

**Alternatives considered**: только `clean()` в форме/админке — обходится прямым ORM/SQL; шесть фиксированных колонок вариантов в `Question` — упрощает `CheckConstraint`, но противоречит отдельной сущности «Вариант ответа» и усложняет админку; немедленный trigger — ломает редактирование набора вариантов.

## 6. Тестирование

**Decision**: стандартный `python manage.py test`. Базовый класс тестов подменяет кэш на `LocMemCache`, очищает его в `setUp` и использует быстрый password hasher. Покрытие по user story: `test_auth_and_topics.py`, `test_attempt_flow.py`, `test_results.py`, `test_leaderboard.py`, `test_admin_integrity.py` (только для trigger — `TransactionTestCase`), `test_cache_invalidation.py`, `test_cache_fallback.py`. Инвалидация проверяется через прогреть → изменить → `captureOnCommitCallbacks(execute=True)` → прочитать; отсутствие SQL — через `assertNumQueries(0)`. В `test_cache_fallback.py` методы `get`/`set`/`delete_many` кэша мокируются так, что выбрасывают `redis.exceptions.ConnectionError`; проверяется, что страница возвращает данные из базы, запрос не падает и `assertLogs` находит предупреждение в `exams.cache`.

**Rationale**: принцип II и SC-005 требуют проверяемого поведения, а не внутренней реализации; `LocMemCache` детерминирован и не требует Valkey в юнит-тестах; `assertNumQueries(0)` точно выражает требование «повторное чтение без БД».

**Alternatives considered**: pytest-django — лишняя зависимость; реальный Valkey в тестах — медленно и зависит от окружения; `TransactionTestCase` везде — медленнее; проверка trigger через `SET CONSTRAINTS ALL IMMEDIATE` внутри `TestCase` — не реальный commit и может скрыть проблему; ручной `cache.clear()` в view — маскирует ошибки инвалидации; тестирование деградации только вручную — не воспроизводимо.

## 7. Docker Compose, healthcheck и запуск

**Decision**: `compose.yaml` с сервисами `db` (`postgres:17-alpine`, volume `pgdata`), `valkey` (`valkey/valkey:8.0.13-alpine`, `--save "" --appendonly no --maxmemory 128mb --maxmemory-policy allkeys-lru`) и `web` (сборка из `Dockerfile`). Healthcheck БД — `pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}`; healthcheck Valkey — `valkey-cli ... ping | grep -q PONG`. `web` имеет `depends_on` с `condition: service_healthy` для обоих сервисов. Проброс `8001:8000`. Entrypoint: `collectstatic --noinput`, `migrate --noinput`, `load_demo_data`, затем gunicorn на `0.0.0.0:8000` с 2 worker.

**Rationale**: по документации Valkey `PING` → `PONG` — простой и достаточный признак готовности отвечать на команды; `pg_isready` проверяет готовность PostgreSQL. Условия `service_healthy` убирают ошибки «connection refused» при старте. Порт 8001 не конфликтует с vibe-версией.

**Alternatives considered**: TCP-проверки (`nc -z`) — слабее; `redis-cli` вместо `valkey-cli` — чужие утилиты; отдельный one-shot `migrate`-сервис — больше движущихся частей; `runserver` — нарушает принцип V.

## 8. Конфигурация, секреты и идемпотентные демо-данные

**Decision**: `.env` (не коммитится) содержит `DEBUG`, `SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `POSTGRES_*`, `VALKEY_*`; `.env.example` содержит те же ключи с заглушками; `.dockerignore` исключает `.git`, `.env`, `__pycache__/`, `.venv/`, `staticfiles/`, тесты/артефакты где применимо. Команда `load_demo_data` вызывается при старте и вручную; она использует стабильные `slug` и `get_or_create` в `transaction.atomic()`, 3 темы × 12 вопросов, не перезаписывает существующие записи.

**Rationale**: принцип III запрещает секреты в git; assumption spec требует, чтобы повторное развёртывание не перезаписывало пользовательские данные и правки администратора; FR-017/SC-006 требуют готовых демо-данных сразу после запуска.

**Alternatives considered**: `loaddata` с фиксированными PK — конфликты и перезапись; data-миграция — всегда применяется и не отключается; `update_or_create` — сотрёт правки админки; natural key по тексту — дубли после редактирования.

## Источники

- Django 5.2 docs, cache framework: `https://github.com/django/django/blob/5.2.18/docs/topics/cache.txt` (через context7).
- Django 5.2 docs, transactions, signals, constraints, testing tools: страницы `/docs/topics/db/transactions.md`, `/docs/ref/signals.md`, `/docs/ref/models/constraints.txt`, `/docs/topics/testing/tools.txt` репозитория Django 5.2.18 (через context7).
- Valkey 8.0.13 docs, installation, protocol, PING: `https://github.com/valkey-io/valkey-doc/tree/8.0.13` (через context7).
- redis-py v5.2 docs, exceptions и retry: `https://github.com/redis/redis-py/blob/v5.2.0/docs/exceptions.rst`, `.../docs/retry.rst` (через context7).
