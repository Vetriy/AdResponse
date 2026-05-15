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
5. Open `/admin/users` and show Russian role labels.
6. Open `/admin/knowledge-base` and show categories and prepared comment cards.
7. Add a prepared manager comment for a category.
8. Logout and login as `client`.
9. Open `/chat/` and send a neutral cost request with an attachment.
10. Show Russian category, Russian tone, clarifying questions and safe answer.
11. Return to `/client/dashboard`, open the appeal and continue the same dialogue.
12. Click `Новое обращение` and show that a separate appeal is created.
13. Send a negative or low-leads request after viewing a report scenario.
14. Show tone-aware response that reduces negativity and offers manager handover.
15. Logout and login as `manager`.
16. Open `/manager/`.
17. Show grouped appeal list, filters, client identifier, `Обращение №...` and sorting by latest client activity.
18. Open `/manager/clients` and show client summary with total/active appeals and last report date.
19. Open appeal detail.
20. Accept the appeal and explain that it закрепляет диалог за менеджером.
21. Upload an advertising report for the client.
22. Send a manual manager response with an attachment.
23. Finish the appeal.
24. Login as client, show report in dashboard, ask a report-related question and rate the completed appeal.
25. Like/dislike an automatic answer and show the aggregate on admin dashboard.
26. Send `Как вам котик?` and show the polite redirect to advertising context.
27. Explain fallback mode and optional local `llama.cpp` mode.

## What to emphasize

- No external cloud LLM APIs are used.
- The app is a modular monolith.
- Data is stored in PostgreSQL.
- The LLM path is optional and local.
- Fallback works even without `llama.cpp`.
- The model prompt includes safety rules and prepared manager comments.
- Reports are stored locally; the assistant uses report title/description as context but does not parse file contents.

## Final functional checklist

- [ ] Client can send a message.
- [ ] Login/logout works.
- [ ] Role-specific navigation works.
- [ ] Role-specific navigation has no duplicated primary items.
- [ ] Admin dashboard statistics are visible.
- [ ] Admin dashboard chart-like analytics are visible.
- [ ] Role labels are displayed in Russian.
- [ ] Message is stored.
- [ ] Message attachments can be uploaded and reopened.
- [ ] Request is classified.
- [ ] Emotional tone is detected.
- [ ] Statuses, categories and tones are displayed in Russian.
- [ ] Prepared comments are selected.
- [ ] Fallback or llama.cpp response is generated.
- [ ] Fallback answers vary by emotional tone.
- [ ] New client appeal is separate from continuing an old appeal.
- [ ] Manager can view appeals.
- [ ] Manager can distinguish clients by identifier.
- [ ] Manager can accept an appeal.
- [ ] Manager can send a manual response.
- [ ] Manager can upload an advertising report for a client.
- [ ] Manager can open the clients section.
- [ ] Manager can finish an appeal.
- [ ] Client can rate a completed appeal.
- [ ] Client can like/dislike an automatic answer.
- [ ] Unusual questions receive a human, advertising-context fallback answer.
- [ ] Client can see advertising reports and ask a question about a report.
- [ ] Admin can manage categories.
- [ ] Admin can manage prepared comments.
- [ ] Documentation explains setup and usage.

## Honest limitations

- No production deployment scripts.
- No advanced semantic search for knowledge base comments.
- Local NLP uses keyword rules.
- Report files are not parsed automatically; only title and description are used as context.
- llama.cpp quality depends on the local model selected by the user.
- No model files are included.
