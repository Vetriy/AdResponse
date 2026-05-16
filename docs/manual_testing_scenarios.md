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
- emotional tone is not shown in the client UI;
- response asks clarifying questions and does not invent exact price.
- response explains that price depends on niche, region, channels and scope.
- response does not expose internal phrases about prepared manager comments, fallback, llama.cpp or system rules.
- response wording is friendly and differs from anxious or negative responses.
- each system answer has `Нравится` and `Не нравится` controls.

Continue the same appeal with:

```text
Регион Москва, бюджет до 80 тысяч.
```

Expected:

- the next response uses the previous dialogue context;
- the assistant does not ask again for region or budget;
- the answer does not copy prepared manager comments as raw text.

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
- emotional tone is not shown in the client UI, but remains available in manager/admin views;
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
- dashboard groups show `Без менеджера`, `Закреплено за мной`, `Закреплено за другим менеджером`, `Завершено`;
- assigned manager becomes the current manager;
- helper text explains that accepting means закрепить диалог за собой;
- manager message appears in dialogue history;
- appeal status is shown as `Менеджер ответил`.
- automatic response source is shown as `Автоматический ответ`, not `local_rules`.

## 9. File upload in dialogue

Steps:

1. Login as `client`.
2. Open `/chat/`.
3. Send a message with a `.png` or `.pdf` attachment under 10 MB.
4. Login as `manager`.
5. Open the appeal and send a manual answer with a `.txt` or `.xlsx` attachment.

Expected:

- attachments are saved locally in `storage/uploads/`;
- images show a preview in the dialogue;
- documents show a filename link;
- executable files are rejected.

## 10. Manager uploads advertising report

Steps:

1. Login as `manager`.
2. Open an appeal for a client.
3. In `Загрузить отчет клиенту`, enter title, description and upload a `.pdf` or `.xlsx`.
4. Login as `client`.
5. Open `/client/dashboard`.
6. Open the single `Отчеты по рекламе` chat.
7. Send a question about the report.

Expected:

- report appears in `Отчеты по рекламе`;
- upload does not show `Клиент обращения не найден` for a registered client appeal;
- client can download/open the report;
- report question is saved in the same persistent report chat, not in a new report chat.
- if report-chat auto replies are enabled, the assistant answers in the same report chat using report title/description context;
- response says only that it uses report title/description and does not pretend to parse the file contents automatically;
- if manager disables report-chat auto replies, the client message is saved without a system answer.

## 11. Admin adds prepared manager comment

Steps:

1. Logout from manager account.
2. Login as `admin`.
3. Open `/admin/dashboard` and review statistics cards.
4. Open `/admin/knowledge-base`.
5. Click `Добавить` for comments.
6. Select category, tone, title and priority.
7. Save.

Expected:

- role labels are shown as `Клиент`, `Менеджер`, `Администратор`;
- comment appears in the list;
- active comment can be selected by response generation for matching category and tone.
- prepared comments are readable as wide cards without horizontal scrolling at normal desktop width.
- `Приоритет` is shown in its own clear area, and edit/delete buttons align consistently.
- category toggle says `Выключить` for active categories and `Включить` for inactive categories;
- after toggling, the page returns to the categories section.
- prepared comment toggle says `Выключить` for active comments and `Включить` for inactive comments;
- after toggling a prepared comment, the page returns to the comments section;
- disabled categories and disabled comments are not used for new generated responses.
- disabling a category also disables its prepared comments;
- enabling the category again does not automatically re-enable its comments.

## 12. Manager finishes appeal and client rates manager

Steps:

1. Login as `manager`.
2. Open an assigned appeal.
3. Click `Завершить обращение`.
4. Login as the client who owns the appeal.
5. Open the completed appeal.
6. Select a rating from 1 to 5 and optionally add a comment.

Expected:

- appeal status becomes `Закрыто`;
- the client sees the manager rating form;
- duplicate rating is rejected or not shown after the first rating;
- manager dashboard/detail shows average rating and number of rated completed appeals.

## 13. AI answer like/dislike

Steps:

1. Login as `client`.
2. Open an appeal with an automatic system answer.
3. Click `Нравится`.
4. Click `Не нравится`, choose `Слишком общий ответ`, and save.
5. Login as `admin` and open `/admin/dashboard`.

Expected:

- the selected feedback is saved;
- only one feedback button is visually active at once;
- custom reason appears only after selecting `Другое`;
- admin dashboard shows total likes, dislikes, helpfulness percentage and dislike reason distribution.

## 14. Manager clients section

Steps:

1. Login as `manager`.
2. Open `/manager/clients`.

Expected:

- all registered clients are visible;
- client type is visible to manager/admin as `Действующий клиент` or `Потенциальный клиент`;
- each row shows client identifier, name/login/email, total appeals, active appeals, last appeal date and last uploaded report date.
- `К обращениям` opens `/manager/dashboard` filtered by that client;
- the dashboard heading says `Обращения клиента: ...` and has `Все обращения`.
- active clients have an `Отчеты` action that opens one persistent report chat;
- potential clients do not have the report chat action.
- active clients are listed before potential clients;
- changing client type in the dropdown saves automatically without a separate `Сохранить` button.

## 15. Unusual question fallback

Message:

```text
Как вам котик?
```

Expected:

- response is polite and light;
- response redirects to advertising context;
- response asks 1-2 useful questions;
- response does not expose internal words like `fallback`, `llama.cpp`, `local_rules`, `prompt`.

## 16. Fallback when llama.cpp is disabled

Set:

```bash
export USE_LLAMA=false
```

Expected:

- `generated_responses.source = local_rules`.

## 17. Fallback when llama.cpp is unavailable

Set:

```bash
export USE_LLAMA=true
```

Do not start `llama-server`.

Expected:

- user still receives a response;
- `generated_responses.source = local_rules`.

## 18. Client types and report visibility

Steps:

1. Login as `admin`.
2. Open `/admin/users`.
3. Edit a client and set type to `Потенциальный клиент`.
4. Login as that client and open `/client/dashboard`.
5. Change the type back to `Действующий клиент` and open the client dashboard again.

Expected:

- admin user table shows the client type and allows editing it;
- potential client does not see `Отчеты по рекламе`;
- active client sees `Отчеты по рекламе`.

## 19. Manager disables automatic answers

Steps:

1. Login as `manager`.
2. Open an appeal and click `Принять обращение`.
3. Confirm `Автоответы: выключены`.
4. Login as client and send a new message in the same appeal.

Expected:

- client message is saved;
- no new automatic system response appears;
- appeal status moves to manager attention.
- client sees one static banner about disabled auto replies, not a repeated system bubble after each message.

## 20. Unread indicators

Steps:

1. Client sends a message in an appeal or report chat.
2. Login as manager and open `/manager/dashboard` or `/manager/clients`.
3. Open the corresponding chat.
4. Return to the list.

Expected:

- unread badge appears before opening;
- after opening, the badge for that role disappears.

## 21. Message layout

Open client appeal detail, manager appeal detail and both report-thread pages.

Expected:

- date separator appears once per day: `Сегодня`, `Вчера` or `dd.mm.yyyy`;
- send time appears at the bottom of every bubble;
- client message metadata shows the client name only;
- manager message metadata shows manager name and `Менеджер`;
- automatic system response has no top name/signature;
- attachments remain visible and readable inside the message bubble.
