# Контракт кэша

**Backend**: `django.core.cache.backends.redis.RedisCache`, `LOCATION` строится из `VALKEY_HOST`, `VALKEY_PORT`, `VALKEY_DB`, `VALKEY_PASSWORD` в формате `redis://...`. Пароль экранируется для URL. `redis` — обязательная зависимость клиента; `valkey://` не поддерживается Django.

## Ключи и значения

| Ключ | Содержимое | Когда читается |
|---|---|---|
| `topics:list` | список `{id, slug, title, description, question_count}` | `GET /` |
| `leaderboard:topic:<topic_id>` | список до 10 записей `{place, username, percent}` | `GET /topics/<topic_id>/leaderboard/` |
| `user:best:<user_id>` | список `{topic_id, topic_title, best_percent}` | `GET /results/` |

`KEY_PREFIX`/`VERSION` задаются в `CACHES`; итоговый ключ формируется Django. TTL — страховка (рекомендуется 300 с), основная актуальность обеспечивается инвалидацией. Пустой список — валидное значение, поэтому чтение использует sentinel, а не проверку на `None`.

## Поток чтения (cache-aside)

1. `cache.get(key, SENTINEL)`.
2. При промахе — один запрос к базе, нормализация в простые `dict`/`list`, `cache.set`.
3. При попадании — возврат значения без SQL.
4. QuerySet'ы и модели в кэш не кладутся.

## Инвалидация

Инвалидация выполняется через `transaction.on_commit(..., robust=True)` в сигналах и в сервисе завершения попытки. Стратегия описана рядом с хелперами чтения в `exams/cache.py`.

| Изменение | Удаляемые ключи | Источник события |
|---|---|---|
| `Topic` создан/изменён | `topics:list` | `post_save` |
| `Topic` удалён | `topics:list`, `leaderboard:topic:<id>` | `post_delete` |
| `Question` создана/изменена/удалена | `topics:list` старого и нового topic | `pre_save` + `post_save`/`post_delete` |
| `AnswerOption` создана/изменена/удалена | `topics:list` | `post_save`/`post_delete` |
| `User.username` изменён | все `leaderboard:topic:*` | `post_save` |
| Попытка завершена | `user:best:<user_id>`, `leaderboard:topic:<topic_id>` | `services.complete_attempt()` |

`QuerySet.update()`, `bulk_create()`, `bulk_update()` и raw SQL не посылают сигналы: такие места обязаны явно вызывать те же функции инвалидации. `cache.clear()` не используется в прикладном коде.

## Гарантии и проверки

- `topics:list` и `leaderboard:topic:<id>` доступны всем вошедшим пользователям и не содержат чужих попыток.
- `user:best:<user_id>` строится только для текущего пользователя.
- Разбор попытки не кэшируется.
- Тесты с `LocMemCache` проверяют: повторное чтение — `assertNumQueries(0)`; после изменения — `captureOnCommitCallbacks(execute=True)` и новое значение; при rollback инвалидация не выполняется.
