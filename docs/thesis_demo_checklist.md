# Thesis Demo Checklist

## Before the defense

- [ ] PostgreSQL is running.
- [ ] `.env` contains a valid `DATABASE_URL`.
- [ ] Dependencies are installed.
- [ ] Migrations are applied.
- [ ] Seed data is loaded.
- [ ] Tests pass.
- [ ] App starts locally.
- [ ] Demo users can login: `admin/admin123`, `manager/manager123`, `client/client123`.

Commands:

```bash
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
python3 -m app.db.seed
pytest
uvicorn app.main:app --reload
```

## Demo flow

1. Open the home page and briefly explain the goal.
2. Login as `admin`.
3. Show clean admin navigation: `Главная`, `Админ`, `Пользователи`, `База знаний`, `Выход`.
4. Open `/admin/dashboard` and show grouped analytics with local chart-like blocks: users by role, appeals by status group, comments by activity and AI-answer feedback.
5. Show manager rating table on `/admin/dashboard`.
6. Open `/admin/users` and show Russian role labels; quick enable/disable and delete/archive are hidden for administrators.
7. Show client type editing: `Действующий клиент` and `Потенциальный клиент`; explain that clients do not see this internal label.
8. Open `/admin/knowledge-base` and show categories above prepared comment cards.
9. Toggle a category and prepared comment and show `Выключить` / `Включить` changes.
10. Add a prepared manager comment for a category.
11. Logout and login as `client`.
12. Open `/chat/` and send a neutral cost request with an attachment.
13. Show Russian category, clarifying questions and safe answer; note that emotional tone is hidden from the client UI.
14. Return to `/client/dashboard`, open the appeal and continue the same dialogue; show that the next autoanswer uses earlier messages and does not repeat already answered questions.
15. Click `Новое обращение` and show that a separate appeal is created.
16. Send a negative or low-leads request after viewing a report scenario.
17. Show tone-aware response that reduces negativity and offers manager handover.
18. Logout and login as `manager`.
19. Open `/manager/`.
20. Show grouped appeal list, filters, client identifier, `Обращение №...` and sorting by latest client activity.
21. Open `/manager/clients` and show client summary; click `К обращениям` to filter appeals by that client.
22. Open appeal detail.
23. Accept the appeal and explain that it закрепляет диалог за менеджером.
24. Show that accepting the appeal turns off autoanswers for that appeal, and demonstrate the toggle.
25. Upload an advertising report for the active client.
26. Open `/manager/clients`, show active clients first, auto-save client type dropdowns, and the persistent report chat only for active clients.
27. Send a manual manager response with an attachment.
28. Finish the appeal.
29. Login as client, show the single report chat in dashboard, ask a report-related question, show report-chat auto reply behavior and rate the completed appeal.
30. Show message layout: daily separators, bottom send time, client name, manager name with `Менеджер`, and no top signature on automatic responses.
31. Show unread badges before opening a chat and that they disappear after opening.
32. Like/dislike an automatic answer and show the aggregate on admin dashboard.
33. Send `Как вам котик?` and show the polite redirect to advertising context.
34. Explain fallback mode and optional local `llama.cpp` mode.

## What to emphasize

- No external cloud LLM APIs are used.
- The app is a modular monolith.
- Data is stored in PostgreSQL.
- The LLM path is optional and local.
- Fallback works even without `llama.cpp`.
- The model prompt includes safety rules and prepared manager comments.
- Prepared comments are internal source material: client answers should not copy manager instructions or expose phrases about prepared comments.
- Automatic responses use the full current dialogue context and still prioritize the latest client message.
- Reports are stored locally; the assistant uses report title/description as context but does not parse file contents.

## Final functional checklist

- [ ] Client can send a message.
- [ ] Login/logout works.
- [ ] Role-specific navigation works.
- [ ] Role-specific navigation has no duplicated primary items.
- [ ] Admin dashboard statistics are visible.
- [ ] Admin dashboard chart-like analytics are visible.
- [ ] Admin dashboard shows active and potential clients.
- [ ] Admin dashboard shows total, active and inactive prepared comments.
- [ ] Role labels are displayed in Russian.
- [ ] Client type labels are displayed in admin/manager pages.
- [ ] Manager client type dropdown saves automatically and active clients are listed first.
- [ ] Message is stored.
- [ ] Message attachments can be uploaded and reopened.
- [ ] Request is classified.
- [ ] Emotional tone is detected.
- [ ] Statuses and categories are displayed in Russian; tones are visible in manager/admin views and hidden from client views.
- [ ] Prepared comments are selected.
- [ ] Prepared comments are not shown to clients as raw manager instructions.
- [ ] Autoanswers use full dialogue context and do not repeat already answered clarifying questions.
- [ ] Disabled categories and comments are not selected for new responses.
- [ ] Disabling a category disables its prepared comments; re-enabling the category does not silently re-enable comments.
- [ ] Fallback or llama.cpp response is generated.
- [ ] Fallback answers vary by emotional tone.
- [ ] New client appeal is separate from continuing an old appeal.
- [ ] Manager can view appeals.
- [ ] Manager can distinguish clients by identifier.
- [ ] Manager can accept an appeal.
- [ ] Manager can enable/disable autoanswers per appeal.
- [ ] Manager can enable/disable autoanswers in a report thread.
- [ ] Manager can send a manual response.
- [ ] Manager can upload an advertising report for a client.
- [ ] Manager can open the clients section.
- [ ] Manager can finish an appeal.
- [ ] Client can rate a completed appeal.
- [ ] Client can like/dislike an automatic answer.
- [ ] Unusual questions receive a human, advertising-context fallback answer.
- [ ] Client can see advertising reports and ask a question about a report.
- [ ] Active client sees one persistent report chat; potential client does not see reports.
- [ ] Client-facing UI hides emotional tone and shows a static auto-reply-off banner instead of repeated system messages.
- [ ] Message bubbles show one date separator per day and send time at the bottom of every message.
- [ ] Client, manager and system message labels follow the messenger-style rules.
- [ ] Unread indicators appear for manager/client messages and clear after opening.
- [ ] Admin can manage categories.
- [ ] Admin can manage prepared comments.
- [ ] Documentation explains setup and usage.

## Honest limitations

- No production deployment scripts.
- No advanced semantic search for knowledge base comments.
- Read markers are simple per conversation and role, not detailed per-user read receipts.
- Local NLP uses keyword rules.
- Report files are not parsed automatically; only title and description are used as context.
- llama.cpp quality depends on the local model selected by the user.
- No model files are included.
