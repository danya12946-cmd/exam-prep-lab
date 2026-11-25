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

1. `safe_cache_get(key)` — обёртка над `cache.get(key, SENTINEL)`; при ошибке Valkey возвращает тот же sentinel, что и промах.
2. При промахе или ошибке кэша — один запрос к базе, нормализация в простые `dict`/`list`, `safe_cache_set`.
3. При попадании — возврат значения без SQL.
4. QuerySet'ы и модели в кэш не кладутся.

## Отказоустойчивость

Valkey — только ускорение; источник истины — PostgreSQL. Все операции с кэшем выполняются через обёртки `safe_cache_get`, `safe_cache_set` и `safe_cache_delete_many` в `exams/cache.py`. При `redis.exceptions.RedisError` (включая `ConnectionError` и `TimeoutError`) или `OSError` обёртка:

- пишет `logger.warning(..., exc_info=True)` в лог `exams.cache`;
- возвращает sentinel для чтения или ничего не делает для записи/инвалидации;
- не пробрасывает исключение в view, форму или admin.

Общий `Exception` не перехватывается, чтобы не скрывать программные ошибки. Пока Valkey недоступен, инвалидации пропускаются; после восстановления время жизни потенциально устаревшего ключа ограничено TTL (300 с), что укладывается в 5 минут из SC-007, а при перезапуске Valkey без persistence кэш пуст.

## Инвалидация

Инвалидация выполняется через `transaction.on_commit(..., robust=True)` в сигналах и в сервисе завершения попытки; удаление ключей идёт через `safe_cache_delete_many`, поэтому ошибка Valkey не отменяет commit базы. Стратегия описана рядом с хелперами чтения в `exams/cache.py`.

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
- Тесты целостности вариантов ответа используют `TransactionTestCase`: отложенный trigger проверяется только при реальном commit, обычный `TestCase` его не проверяет.
- `test_cache_fallback.py` проверяет, что при `redis.exceptions.ConnectionError` на `get`/`set`/`delete_many` страница отдаёт данные из PostgreSQL, запрос завершается успешно и `assertLogs` находит предупреждение в логе `exams.cache`.
