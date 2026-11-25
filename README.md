# Exam Prep Lab

Лабораторная работа по разработке с AI-агентом: веб-приложение для подготовки к экзамену
(темы, тесты из случайных вопросов, разбор ошибок, история результатов).

Приложение сделано двумя способами:
- **`vibe/`** — вайбкодинг: свободные запросы к агенту + ревью (оценка «4»)
- **`sdd/`** — Spec-Driven Development: спека → план → задачи → реализация, кэш на Valkey (оценка «5»)

## Стек
Python 3.12 · Django 5.2 · PostgreSQL 17 · Docker Compose · gunicorn · whitenoise · Bootstrap 5
AI-агент: [opencode](https://opencode.ai) + MCP-сервер context7

## Требования
- Docker и Docker Compose
- (опционально) opencode — для работы с агентом

Проще всего открыть репозиторий в **GitHub Codespaces**: Code → Codespaces → Create codespace.
Docker там уже установлен.

## Запуск (vibe-версия)
```bash
cd vibe
cp .env.example .env          # затем при необходимости поменяйте пароли в .env
docker compose up --build -d  # сборка и запуск контейнеров web и db
docker compose exec web python manage.py load_demo_data    # демо-вопросы
docker compose exec web python manage.py createsuperuser   # админ для /admin/
```
Сайт: http://localhost:8000 (в Codespaces — вкладка **Ports** → порт 8000).

Тесты:
```bash
docker compose exec web python manage.py test
```

Остановка: `docker compose down` (данные базы сохраняются в томе `postgres_data`).

## Запуск (SDD-версия, с Valkey)
```bash
cd sdd
cp .env.example .env
docker compose up --build -d
docker compose exec web python manage.py test
```
Сайт: порт **8001** (в Codespaces — вкладка Ports). Демо-данные загружаются автоматически.

## Структура репозитория
```
.
├── AGENTS.md                  # инструкции для AI-агента
├── opencode.jsonc             # настройка opencode: MCP-сервер context7
├── .opencode/skills/          # свои skills агента
│   └── git-commit/SKILL.md
├── vibe/                      # приложение, сделанное вайбкодингом
│   ├── config/                # настройки Django (settings, urls)
│   ├── exams/                 # приложение: модели, представления, тесты, команды
│   ├── templates/             # HTML-шаблоны
│   ├── Dockerfile
│   ├── compose.yaml
│   └── .env.example
├── sdd/                       # приложение по SDD (в работе)
└── docs/                      # отчёты и скриншоты
    ├── report-3.md
    ├── report-4.md
    └── vibe-log.md
```

## Отчёты
- [Оценка «3»: агент, MCP, Skill, AGENTS.md](docs/report-3.md)
- [Оценка «4»: вайбкодинг приложения](docs/report-4.md)
- [Оценка «5»: SDD + Valkey, сравнение подходов](docs/report-5.md)