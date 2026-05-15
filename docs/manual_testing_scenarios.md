# Manual Testing Scenarios

Before testing:

```bash
source .venv/bin/activate
alembic upgrade head
python3 -m app.db.seed
export USE_LLAMA=false
uvicorn app.main:app --reload
```

Demo accounts:

- `admin` / `admin123`
- `manager` / `manager123`
- `client` / `client123`

## 1. Neutral service cost request

Login as `client`.

Open `/client/dashboard`, then click `Новое обращение` or open `/chat/`.

Message:

```text
Сколько стоит запуск рекламы для салона красоты?
```

Expected:

- category is shown as `Стоимость услуг`;
- tone is shown as `Нейтральный` or `Заинтересованный`;
- response asks clarifying questions and does not invent exact price.
- response does not expose internal phrases about prepared manager comments, fallback, llama.cpp or system rules.

## 2. Campaign launch request

Message:

```text
Хотим запустить рекламную кампанию для новой услуги в Москве.
```

Expected:

- category is shown as `Запуск рекламной кампании`;
- response asks about product, audience, region, site or materials if missing.

## 3. Negative request about poor results

Message:

```text
Мы недовольны результатами рекламы, заявок почти нет, ожидали лучше.
```

Expected:

- category is shown as `Мало заявок` or `Недовольство результатами`;
- tone is shown as `Недовольный`;
- calm supportive response;
- manager handover is offered.

## 4. Low number of leads

Message:

```text
У нас мало лидов и мало заявок за последний месяц.
```

Expected:

- category is shown as `Мало заявок`;
- response asks about period, channel and current metrics;
- handover may be offered.

## 5. Limited budget

Message:

```text
Бюджет ограничен, хотим начать с минимальной суммы.
```

Expected:

- category is shown as `Ограниченный бюджет`;
- response asks about upper budget boundary and priority goal.

## 6. Contact manager request

Message:

```text
Хочу поговорить с менеджером, позвоните мне.
```

Expected:

- category is shown as `Связь с менеджером`;
- handover is offered;
- appeal appears in manager dashboard.

## 7. New appeal is separate from existing appeal

Steps:

1. Login as `client`.
2. Create one appeal through `/chat/`.
3. Return to `/client/dashboard`.
4. Open the created appeal and send a continuation message.
5. Return to `/client/dashboard`.
6. Click `Новое обращение` and send a different message.

Expected:

- continuation message is saved in the selected old appeal;
- the second message from `/chat/` creates a separate appeal;
- after logout/login, old appeals are still visible in `/client/dashboard`;
- client cannot open another client's appeal by changing the URL id.

## 8. Manager accepts appeal and sends manual response

Steps:

1. Logout from client account.
2. Login as `manager`.
3. Open `/manager/`.
4. Open the created appeal.
5. Click `Принять обращение`.
6. Enter a manual answer.
7. Submit.

Expected:

- manager dashboard shows a clear client identifier;
- assigned manager becomes the current manager;
- manager message appears in dialogue history;
- appeal status is shown as `Менеджер ответил`.

## 9. Admin adds prepared manager comment

Steps:

1. Logout from manager account.
2. Login as `admin`.
3. Open `/admin/knowledge-base`.
4. Click `Добавить` for comments.
5. Select category, tone, title and priority.
6. Save.

Expected:

- comment appears in the list;
- active comment can be selected by response generation for matching category and tone.
- prepared comments block is wide and readable without horizontal scrolling at normal desktop width.

## 10. Fallback when llama.cpp is disabled

Set:

```bash
export USE_LLAMA=false
```

Expected:

- `generated_responses.source = local_rules`.

## 11. Fallback when llama.cpp is unavailable

Set:

```bash
export USE_LLAMA=true
```

Do not start `llama-server`.

Expected:

- user still receives a response;
- `generated_responses.source = local_rules`.
