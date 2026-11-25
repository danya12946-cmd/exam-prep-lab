# Отчёт: оценка «3» — агент, MCP, Skill, AGENTS.md

## Окружение
- Среда: GitHub Codespaces (Linux, Docker, Python, Node.js)
- Агент: opencode 1.19.6
- Модели: DeepSeek V4.1 Flash Free, Big Pickle (бесплатные модели OpenCode Zen)

> Docker Desktop на локальной Windows не установился: в системе отсутствуют компоненты
> VirtualMachinePlatform и WSL (ошибка DISM 0x800f080c), поэтому работа велась в Codespaces.

## 1. Запуск агента
```bash
curl -fsSL https://opencode.ai/install | bash
opencode
```
Модель выбрана командой `/models`.

## 2. MCP-сервер context7
Context7 даёт агенту доступ к актуальной документации библиотек (Django, PostgreSQL, Valkey),
чтобы он не опирался только на устаревшие знания из обучения.

Подключение:
```bash
opencode mcp add context7 --url https://mcp.context7.com/mcp
opencode mcp list
```
Команда записала настройку в глобальный конфиг `~/.config/opencode/opencode.jsonc`.
Чтобы она была частью проекта, файл перенесён в корень репозитория:
[`opencode.jsonc`](../opencode.jsonc). Ключей и паролей в нём нет.

Проверка: на запрос «найди в документации Django, как подключить PostgreSQL» агент вызвал
инструменты `context7_resolve-library-id` и `context7_query-docs`, статус сервера — `context7 Connected`.
Ответ был собран из официальной документации Django.

## 3. AGENTS.md
Файл [`AGENTS.md`](../AGENTS.md) — постоянные инструкции для агента: описание проекта,
структура репозитория, команды запуска и правила работы (язык общения, секреты только в `.env`,
обязательный запуск тестов, использование context7, коммиты через skill, без push без просьбы).
opencode автоматически загружает его в начале каждой сессии.

## 4. Свой Skill: git-commit
Файл [`.opencode/skills/git-commit/SKILL.md`](../.opencode/skills/git-commit/SKILL.md).
Skill описывает, как агенту делать аккуратные коммиты: посмотреть изменения, проверить, что не
попали секреты, разбить изменения на логические коммиты, оформить сообщение по Conventional Commits
на русском.

Агент выбирает skill по полю `description`, когда пользователь просит сделать коммит.
Пример результата — коммиты в истории репозитория:
- `chore(opencode): добавить AGENTS.md и skill git-commit`
- `chore(opencode): подключить MCP-сервер context7`
- `fix(config): выключить DEBUG по умолчанию`

Skill использовался на всех следующих этапах: вся история коммитов проекта оформлена по нему.

## Вывод
Агент opencode запущен с бесплатной моделью, подключён MCP-сервер context7 для актуальной
документации, написан skill для коммитов и AGENTS.md с правилами проекта. Эта настройка
использовалась при разработке обеих версий приложения (vibe и SDD).