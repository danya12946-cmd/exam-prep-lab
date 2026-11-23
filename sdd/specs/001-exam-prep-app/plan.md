# Implementation Plan: Веб-приложение для подготовки к экзамену

**Branch**: `001-exam-prep-app` | **Date**: 2026-11-23 | **Spec**: `specs/001-exam-prep-app/spec.md`

**Input**: User description: технический стек и решения из задания; функциональные требования — `specs/001-exam-prep-app/spec.md`.

## Summary

Реализовать монолитное Django-приложение для подготовки к экзамену: регистрация/вход, список тем, прохождение теста из 10 случайных вопросов с разбором, история и лучшие результаты пользователя, таблицы лидеров по темам, администрирование контента с сохранением неизменяемых снимков в завершённых попытках. Стек разворачивается одной командой Docker Compose: PostgreSQL 17 хранит данные, Valkey 8 используется как кэш через штатный `RedisCache`, gunicorn раздаёт приложение, whitenoise — статику, интерфейс оформлен Bootstrap 5 через CDN. Кэш читается по шаблону cache-aside и инвалидируется сигналами Django с учётом транзакций; при недоступности Valkey операции с кэшем пропускаются с логированием, а данные берутся из PostgreSQL. Состояние незавершённой попытки хранится в базе, а не в сессии.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: Django 5.2 LTS; `psycopg[binary]` для PostgreSQL; `redis` как обязательный клиент для `django.core.cache.backends.redis.RedisCache`; gunicorn; whitenoise; Bootstrap 5 через CDN. Дополнительных сервисов и ORM нет.

**Storage**: PostgreSQL 17 (основная база, постоянный volume); Valkey 8 (кэш, извлекаемые данные); статические файлы собираются в `staticfiles/` и отдаются whitenoise.

**Testing**: стандартный Django test runner (`python manage.py test`); в тестах кэш подменяется на `LocMemCache` через `@override_settings`; проверки инвалидации используют `captureOnCommitCallbacks(execute=True)`, проверки отсутствия SQL — `assertNumQueries(0)`. Тесты целостности вариантов ответа используют `TransactionTestCase`: отложенный trigger срабатывает только при реальном commit. Отдельный `test_cache_fallback.py` проверяет, что при ошибке Valkey приложение продолжает работать на данных из базы и пишет предупреждение в лог.

**Target Platform**: Linux-контейнер, Docker Compose; сайт доступен на `http://localhost:8001`, vibe-версия занимает порт 8000.

**Project Type**: веб-приложение (серверные HTML-страницы, Django templates, Django admin).

**Performance Goals**: повторное чтение списка тем, таблицы лидеров и лучших результатов пользователя выполняется без обращений к базе, пока данные не изменились (SC-005); после изменения данных страницы сразу показывают актуальные значения (FR-019). Нагрузка учебная — десятки одновременных пользователей; отдельный SLA по времени отклика в спецификации не задан.

**Constraints**:
- `DEBUG=False` по умолчанию; секреты только в `.env`, в git только `.env.example`; обязателен `.dockerignore`.
- Все внутренние страницы доступны только вошедшим пользователям; доступ к попытке проверяется серверной фильтрацией по `user=request.user`.
- Вопрос имеет от 2 до 6 вариантов и ровно один правильный; ограничения реализованы в базе и проверяются тестом с реальным commit.
- Valkey — только ускорение: при ошибке подключения чтение/запись кэша пропускаются, данные берутся из PostgreSQL, ошибка логируется.
- Завершённые попытки сохраняют снимки вопросов, вариантов и ответов и не меняются после правок администратора.
- Интерфейс и сообщения — на русском; код и имена — на английском.
- Версии образов и пакетов фиксируются; запуск и разработка идут через один и тот же Docker Compose.

**Scale/Scope**: 3 демо-темы по 12 вопросов; до 10 вопросов в попытке; топ-10 в таблице лидеров; история и лучшие результаты по пользователю; постоянный том PostgreSQL; один web-сервис под gunicorn с 2 worker.

**Неопределённостей нет**: все технологические решения заданы пользователем, а функциональные детали — spec.md; `NEEDS CLARIFICATION` отсутствуют.

## Constitution Check

*GATE: проверено до Phase 0 и повторно после Phase 1.*

| Принцип | Статус | Обоснование |
|---|---|---|
| I. Простота | PASS | Один Django-монолит, одно приложение `exams`, только PostgreSQL и Valkey как внешние сервисы. `redis` и `psycopg` нужны штатным бэкендам Django; `gunicorn`/`whitenoise` прямо заданы стеком. Новых абстракций без нескольких потребителей нет. |
| II. Тесты обязательны | PASS | Каждая user story получает тест через Django test runner; отдельные тесты проверяют кэш, инвалидацию, ограничения и контроль доступа. Ограничения вариантов проверяются в `TransactionTestCase` с реальным commit; тест деградации Valkey проверяет наблюдаемое поведение. Тесты запускаются до завершения работы. |
| III. Безопасность по умолчанию | PASS | `DEBUG=False`, секреты из `.env`, `.env.example` и `.dockerignore` обязательны; `LoginRequiredMixin`, проверка владельца попытки в запросе, Django admin только для `is_staff`. |
| IV. Целостность данных на уровне базы | PASS | `ForeignKey`, `unique`, `UniqueConstraint`, `CheckConstraint` и отложенный PostgreSQL constraint trigger для «ровно один правильный вариант» описаны в миграциях; проверки форм дополняют, но не заменяют базу. |
| V. Воспроизводимый запуск | PASS | `compose.yaml`, фиксированные версии образов и пакетов, `Dockerfile`, `entrypoint.sh` с `migrate` и идемпотентной загрузкой демо-данных, gunicorn, whitenoise. |
| VI. Производительность и кэширование | PASS | Кэш Valkey для трёх часто читаемых наборов; инвалидация сигналами + `transaction.on_commit` и явными вызовами для bulk/raw-записей; гипотеза нагрузки подтверждается `assertNumQueries(0)`; стратегия описана рядом с кодом чтения. Ошибки Valkey перехватываются и логируются, запрос обслуживается из базы. |
| VII. Язык | PASS | Документы Spec Kit и интерфейс на русском; код, модели, поля, команды и файлы — на английском. |

**Повторная проверка после Phase 1**: нарушений не обнаружено; все проектные решения (снимки попыток, deferred trigger, cache-aside) подтверждают принципы и не меняют стек. В `Complexity Tracking` список нарушений пуст.

## Project Structure

### Documentation (this feature)

```text
specs/001-exam-prep-app/
├── plan.md              # этот файл
├── research.md          # Phase 0: решения и обоснование
├── data-model.md        # Phase 1: сущности, поля, связи, переходы
├── contracts/           # Phase 1: HTTP, CLI и контракт кэша
│   ├── http.md
│   ├── cli.md
│   └── cache.md
├── quickstart.md        # Phase 1: проверка сценариев end-to-end
├── checklists/          # уже созданные чеклисты спецификации
└── tasks.md             # Phase 2, этим планом не создаётся
```

### Source Code (repository root `sdd/`)

```text
sdd/
├── .env.example
├── .dockerignore
├── Dockerfile
├── compose.yaml
├── entrypoint.sh
├── requirements.txt
├── manage.py
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── exams/
│   ├── __init__.py
│   ├── apps.py
│   ├── models.py
│   ├── forms.py
│   ├── cache.py
│   ├── services.py
│   ├── signals.py
│   ├── views.py
│   ├── urls.py
│   ├── admin.py
│   ├── migrations/
│   │   ├── 0001_initial.py
│   │   └── 0002_answer_option_constraints.sql  (через RunSQL в миграции)
│   ├── management/
│   │   └── commands/
│   │       └── load_demo_data.py
│   ├── templates/
│   │   ├── base.html
│   │   └── exams/
│   │       ├── topic_list.html
│   │       ├── attempt_question.html
│   │       ├── attempt_result.html
│   │       ├── result_list.html
│   │       └── leaderboard.html
│   └── tests/
│       ├── test_auth_and_topics.py
│       ├── test_attempt_flow.py
│       ├── test_results.py
│       ├── test_leaderboard.py
│       ├── test_admin_integrity.py       # TransactionTestCase для отложенного trigger
│       ├── test_cache_invalidation.py
│       └── test_cache_fallback.py
└── static/
    └── css/app.css
```

**Structure Decision**: выбран один проект Django в корне `sdd/` с единственным приложением `exams`. Отдельного frontend-проекта нет: страницы серверные, Bootstrap подключается через CDN, собственные стили минимальны. Документы specs лежат рядом с кодом в `sdd/specs/`.

## Complexity Tracking

Нарушений конституции нет; таблица обоснований не требуется.
