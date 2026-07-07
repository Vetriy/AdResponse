# AGENTS.md

## Project

This repository contains a bachelor thesis software project: an interactive online service for primary response to client requests for an advertising agency.

The system must be implemented as a web application with:
- Python backend;
- FastAPI;
- PostgreSQL;
- SQLAlchemy;
- Alembic;
- Jinja2 templates;
- HTML/CSS/Vanilla JavaScript frontend;
- local llama.cpp integration through HTTP API;
- no React, no Next.js, no Firebase, no Supabase, no foreign cloud AI APIs.

## Main idea

The service receives a client message, stores it in the database, classifies the request, detects emotional tone, selects relevant prepared manager comments from the knowledge base, sends the context to a local llama.cpp server, generates a primary response, stores the response, and displays it to the client.

If the request is negative, complex, or lacks information, the service must ask clarifying questions or transfer the dialogue to a manager with preserved context.

## Legal and architectural constraints

- Do not use external cloud LLM APIs.
- Do not use OpenAI API, Claude API, Gemini API, Hugging Face Inference API, Firebase, Supabase, Vercel, Netlify, AWS, Azure, or Google Cloud.
- All data processing must be designed for local deployment or deployment on a server located in the Russian Federation.
- The LLM must be local and accessed through llama.cpp.
- Do not require paid services.
- Do not use React.
- Do not use Docker Desktop. If container instructions are needed, prefer Podman-compatible commands.
- The project must be cross-platform.

## Code style

- Keep the implementation simple and understandable for a bachelor thesis.
- Prefer modular monolith architecture.
- Keep files small and readable.
- Use clear names for modules, functions, classes, and database tables.
- Add comments only where they explain non-obvious logic.
- Do not over-engineer.
- Do not introduce microservices.

## Required architecture

Use this approximate structure:

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
alembic/
tests/
README.md

## Expected modules

- chat module;
- appeals module;
- manager dashboard;
- knowledge base module;
- classification module;
- sentiment analysis module;
- llama.cpp adapter;
- response generation module.

## Development rules

Before making large changes:
1. Inspect the current repository.
2. Explain the planned changes briefly.
3. Make the smallest useful change.
4. Run or provide the relevant test/start command.
5. Summarize changed files.

Do not rewrite the entire project unless explicitly asked.

## UI and visual design requirements

The project must have a clean, modern, thesis-friendly interface in soft pastel colors.

Design style:
- pastel color palette;
- light background;
- soft shadows;
- rounded cards and buttons;
- calm advertising agency aesthetic;
- no aggressive colors;
- no dark cyberpunk style;
- no default unstyled HTML;
- responsive layout for desktop and mobile;
- readable typography;
- enough spacing between blocks;
- accessible color contrast.

Preferred colors:
- warm off-white background;
- pastel lavender;
- pastel blue;
- soft mint;
- light peach;
- muted gray text.

Frontend restrictions:
- Do not use React.
- Do not use Next.js.
- Do not use Tailwind CDN.
- Do not use Bootstrap CDN.
- Do not use external Google Fonts.
- Do not use external icon libraries from CDN.
- Use local CSS files only.
- Use system fonts.
- Use HTML, CSS, Jinja2 templates, and Vanilla JavaScript only.

Required pages must look visually consistent:
- home page;
- client chat page;
- manager dashboard;
- appeal detail page;
- admin knowledge base pages.