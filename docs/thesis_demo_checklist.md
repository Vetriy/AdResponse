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
4. Open `/admin/users` and show role-based accounts.
5. Open `/admin/knowledge-base` and show categories and the wide prepared comments block.
6. Add a prepared manager comment for a category.
7. Logout and login as `client`.
8. Open `/chat/` and send a neutral cost request.
9. Show Russian category, Russian tone, clarifying questions and safe answer.
10. Return to `/client/dashboard`, open the appeal and continue the same dialogue.
11. Click `Новое обращение` and show that a separate appeal is created.
12. Send a negative or low-leads request.
13. Show supportive answer and manager handover recommendation.
14. Logout and login as `manager`.
15. Open `/manager/`.
16. Show the appeal list, filters and client identifier.
17. Open appeal detail.
18. Accept the appeal.
19. Send a manual manager response.
20. Show that the client sees the manager answer in the same appeal history.
21. Explain fallback mode and optional local `llama.cpp` mode.

## What to emphasize

- No external cloud LLM APIs are used.
- The app is a modular monolith.
- Data is stored in PostgreSQL.
- The LLM path is optional and local.
- Fallback works even without `llama.cpp`.
- The model prompt includes safety rules and prepared manager comments.

## Final functional checklist

- [ ] Client can send a message.
- [ ] Login/logout works.
- [ ] Role-specific navigation works.
- [ ] Role-specific navigation has no duplicated primary items.
- [ ] Message is stored.
- [ ] Request is classified.
- [ ] Emotional tone is detected.
- [ ] Statuses, categories and tones are displayed in Russian.
- [ ] Prepared comments are selected.
- [ ] Fallback or llama.cpp response is generated.
- [ ] New client appeal is separate from continuing an old appeal.
- [ ] Manager can view appeals.
- [ ] Manager can distinguish clients by identifier.
- [ ] Manager can accept an appeal.
- [ ] Manager can send a manual response.
- [ ] Admin can manage categories.
- [ ] Admin can manage prepared comments.
- [ ] Documentation explains setup and usage.

## Honest limitations

- No production deployment scripts.
- No advanced semantic search for knowledge base comments.
- Local NLP uses keyword rules.
- llama.cpp quality depends on the local model selected by the user.
- No model files are included.
