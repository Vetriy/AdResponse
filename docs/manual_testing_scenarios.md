# Manual Testing Scenarios

Before testing:

```bash
source .venv/bin/activate
alembic upgrade head
python3 -m app.db.seed
export USE_LLAMA=false
uvicorn app.main:app --reload
```

## 1. Neutral service cost request

Message:

```text
Сколько стоит запуск рекламы для салона красоты?
```

Expected:

- category: `service cost`;
- tone: `neutral` or `interested`;
- response asks clarifying questions and does not invent exact price.

## 2. Campaign launch request

Message:

```text
Хотим запустить рекламную кампанию для новой услуги в Москве.
```

Expected:

- category: `campaign launch`;
- response asks about product, audience, region, site or materials if missing.

## 3. Negative request about poor results

Message:

```text
Мы недовольны результатами рекламы, заявок почти нет, ожидали лучше.
```

Expected:

- category: `low number of leads` or `dissatisfaction with campaign results`;
- tone: `disappointed`;
- calm supportive response;
- manager handover is offered.

## 4. Low number of leads

Message:

```text
У нас мало лидов и мало заявок за последний месяц.
```

Expected:

- category: `low number of leads`;
- response asks about period, channel and current metrics;
- handover may be offered.

## 5. Limited budget

Message:

```text
Бюджет ограничен, хотим начать с минимальной суммы.
```

Expected:

- category: `limited budget`;
- response asks about upper budget boundary and priority goal.

## 6. Contact manager request

Message:

```text
Хочу поговорить с менеджером, позвоните мне.
```

Expected:

- category: `contact manager request`;
- handover is offered;
- appeal appears in manager dashboard.

## 7. Manager accepts appeal and sends manual response

Steps:

1. Open `/manager/`.
2. Open the created appeal.
3. Click `Принять обращение`.
4. Enter a manual answer.
5. Submit.

Expected:

- assigned manager becomes `Дежурный менеджер`;
- manager message appears in dialogue history;
- appeal status becomes `manager_answered`.

## 8. Admin adds prepared manager comment

Steps:

1. Open `/admin/knowledge-base`.
2. Click `Добавить` for comments.
3. Select category, tone, title, text and priority.
4. Save.

Expected:

- comment appears in the list;
- active comment can be selected by response generation for matching category and tone.

## 9. Fallback when llama.cpp is disabled

Set:

```bash
export USE_LLAMA=false
```

Expected:

- `generated_responses.source = local_rules`.

## 10. Fallback when llama.cpp is unavailable

Set:

```bash
export USE_LLAMA=true
```

Do not start `llama-server`.

Expected:

- user still receives a response;
- `generated_responses.source = local_rules`.
