# Thesis Demo Checklist

## Before the defense

- [ ] PostgreSQL is running.
- [ ] `.env` contains a valid `DATABASE_URL`.
- [ ] Dependencies are installed.
- [ ] Migrations are applied.
- [ ] Seed data is loaded.
- [ ] Tests pass.
- [ ] App starts locally.

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
2. Open `/admin/knowledge-base` and show categories and prepared comments.
3. Add a prepared manager comment for a category.
4. Open `/chat/`.
5. Send a neutral cost request.
6. Show category, tone, clarifying questions and safe answer.
7. Send a negative or low-leads request.
8. Show supportive answer and manager handover recommendation.
9. Open `/manager/`.
10. Show the appeal list and filters.
11. Open appeal detail.
12. Accept the appeal.
13. Send a manual manager response.
14. Show that the full dialogue history is preserved.
15. Explain fallback mode and optional local `llama.cpp` mode.

## What to emphasize

- No external cloud LLM APIs are used.
- The app is a modular monolith.
- Data is stored in PostgreSQL.
- The LLM path is optional and local.
- Fallback works even without `llama.cpp`.
- The model prompt includes safety rules and prepared manager comments.

## Final functional checklist

- [ ] Client can send a message.
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
