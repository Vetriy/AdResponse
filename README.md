# AdResponse

Интерактивный веб-сервис для первичного ответа на обращения клиентов рекламного агентства. Проект выполняется как дипломная работа и развивается поэтапно: сначала каркас FastAPI и интерфейс, затем база данных, бизнес-логика и локальная интеграция с `llama.cpp`.

## Текущий этап

Реализован стартовый каркас приложения, слой базы данных, клиентский чат, локальная NLP-логика и опциональная интеграция с локальным `llama.cpp`:

- FastAPI-приложение с модульными роутерами;
- Jinja2-шаблоны;
- локальные CSS и JavaScript без CDN;
- страницы: главная, клиентский чат, панель менеджера, база знаний;
- пастельная адаптивная UI-основа;
- SQLAlchemy ORM-модели доменной области;
- Alembic-миграция для PostgreSQL;
- seed-скрипт с начальными категориями и комментариями базы знаний;
- детерминированная классификация и анализ тональности;
- генерация ответа через локальные правила или локальный `llama.cpp`.

## Локальный запуск

Создать и активировать виртуальное окружение:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Для Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Установить зависимости:

```bash
pip install -r requirements.txt
```

При необходимости создать локальный файл настроек:

```bash
cp .env.example .env
```

Настроить PostgreSQL и указать параметры подключения в `.env`. Можно использовать отдельные переменные `DATABASE_HOST`, `DATABASE_PORT`, `DATABASE_NAME`, `DATABASE_USER`, `DATABASE_PASSWORD` или готовую строку `DATABASE_URL`.

Применить миграции:

```bash
alembic upgrade head
```

Загрузить начальные категории и подготовленные комментарии:

```bash
python3 -m app.db.seed
```

Запустить приложение без `llama.cpp`, только с локальным fallback-ответом:

```bash
export USE_LLAMA=false
uvicorn app.main:app --reload
```

Для запуска с локальным `llama.cpp` нужно поднять сервер в OpenAI-совместимом режиме на endpoint:

```text
http://localhost:8080/v1/chat/completions
```

Пример запуска приложения с включенным `llama.cpp`:

```bash
export USE_LLAMA=true
export LLAMA_BASE_URL=http://localhost:8080/v1/chat/completions
export LLAMA_MODEL_NAME=local-model
export LLAMA_TIMEOUT_SECONDS=20
uvicorn app.main:app --reload
```

Если `llama.cpp` недоступен, отвечает слишком долго или возвращает некорректный ответ, приложение автоматически использует локальную fallback-генерацию на основе подготовленных комментариев.

Открыть в браузере:

- <http://127.0.0.1:8000/>
- <http://127.0.0.1:8000/chat/>
- <http://127.0.0.1:8000/manager/>
- <http://127.0.0.1:8000/admin/knowledge-base>

## Проверка

```bash
pytest
```

## Структура

```text
app/
  main.py
  core/
  db/
  models/
  schemas/
  services/
  routers/
  templates/
  static/
  llama/
docs/
tests/
```

## Ограничения проекта

- не использовать React, Next.js, Tailwind, Bootstrap и внешние CDN;
- не использовать внешние облачные LLM API;
- LLM-интеграция должна работать только локально через `llama.cpp`;
- PostgreSQL не заменяется на SQLite.
