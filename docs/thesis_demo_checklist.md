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
3. Open `/admin/users` and show role-based accounts.
4. Open `/admin/knowledge-base` and show categories and prepared comments.
5. Add a prepared manager comment for a category.
6. Logout and login as `client`.
7. Open `/chat/`.
8. Send a neutral cost request.
9. Show category, tone, clarifying questions and safe answer.
10. Send a negative or low-leads request.
11. Show supportive answer and manager handover recommendation.
12. Logout and login as `manager`.
13. Open `/manager/`.
14. Show the appeal list and filters.
15. Open appeal detail.
16. Accept the appeal.
17. Send a manual manager response.
18. Show that the full dialogue history is preserved.
19. Explain fallback mode and optional local `llama.cpp` mode.

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
- [ ] Message is stored.
- [ ] Request is classified.
- [ ] Emotional tone is detected.
- [ ] Prepared comments are selected.
- [ ] Fallback or llama.cpp response is generated.
- [ ] Manager can view appeals.
- [ ] Manager can accept an appeal.
- [ ] Manager can send a manual response.
- [ ] Admin can manage categories.
- [ ] Admin can manage prepared comments.
- [ ] Documentation explains setup and usage.

## Honest limitations

- No authentication or real user accounts in the UI.
- No production deployment scripts.
- No advanced semantic search for knowledge base comments.
- Local NLP uses keyword rules.
- llama.cpp quality depends on the local model selected by the user.
- No model files are included.
