# AdResponse

Интерактивный веб-сервис для первичного ответа на обращения клиентов рекламного агентства. Проект подготовлен как демонстрационная часть бакалаврской работы: клиент отправляет сообщение, система сохраняет диалог, классифицирует запрос, определяет эмоциональный тон, выбирает подготовленные комментарии менеджера и формирует первичный ответ локально.

## Возможности

- FastAPI backend, Jinja2 templates, HTML/CSS/Vanilla JavaScript.
- PostgreSQL, SQLAlchemy ORM, Alembic migrations.
- Клиентский чат с историей сообщений.
- Детерминированная классификация и анализ тональности.
- Выбор активных комментариев базы знаний по категории, тону и приоритету.
- Fallback-генерация без внешних API.
- Опциональная интеграция с локальным `llama.cpp` через `http://localhost:8080/v1/chat/completions`.
- Панель менеджера: список обращений, детали диалога, принятие обращения, ручной ответ, смена статуса.
- Админ-раздел: CRUD категорий и подготовленных комментариев.
- Ролевая аутентификация и личные кабинеты: `client`, `manager`, `admin`.
- Управление пользователями в админ-разделе.
- Чистая ролевая навигация без дублирующих пунктов.
- Статусы, категории и эмоциональные тона отображаются на русском языке.
- Админ-статистика по пользователям, ролям, обращениям, комментариям и отчетам.
- Загрузка файлов в клиентско-менеджерский диалог без внешнего хранилища.
- Простые рекламные отчеты: менеджер загружает отчет клиенту, клиент видит его в кабинете и может задать вопрос.
- Более тональные fallback-ответы: нейтральные, тревожные и негативные обращения обрабатываются разными формулировками.

## Быстрый запуск

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Настройте PostgreSQL в `.env`, затем:

```bash
alembic upgrade head
python3 -m app.db.seed
export USE_LLAMA=false
uvicorn app.main:app --reload
```

Откройте:

- <http://127.0.0.1:8000/chat/>
- <http://127.0.0.1:8000/manager/>
- <http://127.0.0.1:8000/admin/knowledge-base>

## Демо-пользователи

Seed-скрипт создает пользователей:

| Логин | Пароль | Роль |
| --- | --- | --- |
| `admin` | `admin123` | `admin` |
| `manager` | `manager123` | `manager` |
| `client` | `client123` | `client` |

Чтобы переключиться между ролями, нажмите `Выход` и войдите под другим пользователем.

## Личные кабинеты

- Public: `/`, `/login`, `/register`.
- Client: `/client/dashboard`, `/chat/`, `/client/appeals/{appeal_id}`.
- Manager: `/manager/dashboard`.
- Admin: `/admin/dashboard`, `/admin/users`, `/admin/knowledge-base`.

Клиентская логика:

- `/chat/` и `/client/chat` создают новое обращение.
- Старое обращение продолжается только на странице `/client/appeals/{appeal_id}` из кабинета клиента.
- Клиент видит только собственные обращения.

Менеджерская логика:

- `/manager/dashboard` содержит фильтры и список обращений на одной странице.
- В списке и деталях обращения показан идентификатор клиента: ФИО, логин, email или `Клиент №ID`.
- `Принять обращение` означает закрепить диалог за текущим менеджером и продолжить ручной ответ клиенту.
- В деталях обращения менеджер может загрузить рекламный отчет для клиента.

Файлы и отчеты:

- В чат можно прикреплять `.png`, `.jpg`, `.jpeg`, `.webp`, `.pdf`, `.doc`, `.docx`, `.xls`, `.xlsx`, `.txt`.
- Ограничение размера файла: 10 МБ.
- Файлы сохраняются локально в `storage/uploads/`.
- Исполняемые файлы не разрешены.

## Переменные окружения

```env
APP_NAME=AdResponse
DEBUG=true
SECRET_KEY=change-me-for-local-development

DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=adresponse
DATABASE_USER=adresponse
DATABASE_PASSWORD=adresponse
DATABASE_URL=postgresql+psycopg://adresponse:adresponse@localhost:5432/adresponse

USE_LLAMA=false
LLAMA_BASE_URL=http://localhost:8080/v1/chat/completions
LLAMA_MODEL_NAME=local-model
LLAMA_TIMEOUT_SECONDS=20
```

## Режимы генерации

Fallback mode: `USE_LLAMA=false`. Ответ строится локально по правилам, категории, эмоциональному тону, уточняющим вопросам и подготовленным комментариям.
Клиенту не показываются технические источники вроде `local_rules`; в интерфейсе они отображаются как `Автоматический ответ` или `Локальная языковая модель`.

llama.cpp mode: `USE_LLAMA=true`. Приложение отправляет запрос только на локальный OpenAI-compatible endpoint `LLAMA_BASE_URL`. Если `llama.cpp` недоступен, сработает fallback.

## Тесты

```bash
pytest
python3 -m compileall app tests alembic
```

Тесты не требуют реального `llama.cpp` сервера и не используют внешние облачные сервисы.

## Документация

- [User guide](docs/user_guide.md)
- [Developer guide](docs/developer_guide.md)
- [llama.cpp setup](docs/llama_cpp_setup.md)
- [Manual testing scenarios](docs/manual_testing_scenarios.md)
- [Thesis demo checklist](docs/thesis_demo_checklist.md)

## Ограничения

- Нет production-настроек безопасности.
- NLP-логика простая и детерминированная.
- Загруженные отчеты не анализируются автоматически: используется только название и описание отчета.
- llama.cpp модель и файлы модели не входят в репозиторий.
- Внешние LLM API, React, CDN и облачные AI-сервисы не используются.
