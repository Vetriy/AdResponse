# AdResponse

Интерактивный веб-сервис для первичного ответа на обращения клиентов рекламного агентства. Проект выполняется как дипломная работа и развивается поэтапно: сначала каркас FastAPI и интерфейс, затем база данных, бизнес-логика и локальная интеграция с `llama.cpp`.

## Текущий этап

Реализован стартовый каркас приложения без PostgreSQL, llama.cpp и бизнес-логики:

- FastAPI-приложение с модульными роутерами;
- Jinja2-шаблоны;
- локальные CSS и JavaScript без CDN;
- страницы: главная, клиентский чат, панель менеджера, база знаний;
- пастельная адаптивная UI-основа.

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

Запустить приложение:

```bash
uvicorn app.main:app --reload
```

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
- будущая LLM-интеграция должна работать локально через `llama.cpp`;
- база данных и бизнес-логика будут добавлены отдельными этапами.
