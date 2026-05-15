# llama.cpp Setup

## Purpose

The project can work without `llama.cpp`. When `USE_LLAMA=false`, it uses deterministic fallback generation. When `USE_LLAMA=true`, it sends context to a local OpenAI-compatible `llama.cpp` endpoint.

## Required endpoint

```text
http://localhost:8080/v1/chat/completions
```

The adapter rejects non-local endpoints and expects the `/v1/chat/completions` path.

## Environment

```env
USE_LLAMA=true
LLAMA_BASE_URL=http://localhost:8080/v1/chat/completions
LLAMA_MODEL_NAME=local-model
LLAMA_TIMEOUT_SECONDS=20
```

## Example local server command

The exact binary name depends on how `llama.cpp` was built. A typical local command is:

```bash
./llama-server -m /path/to/model.gguf --host 127.0.0.1 --port 8080
```

Model files are not included and should not be downloaded by the application.

## Run application with llama.cpp

```bash
source .venv/bin/activate
export USE_LLAMA=true
export LLAMA_BASE_URL=http://localhost:8080/v1/chat/completions
export LLAMA_MODEL_NAME=local-model
export LLAMA_TIMEOUT_SECONDS=20
uvicorn app.main:app --reload
```

## Fallback behavior

If `llama.cpp` is disabled, unavailable, too slow, returns invalid JSON, returns empty content, or is configured to a non-local endpoint, the application automatically uses local fallback generation.

## How to verify

1. Start PostgreSQL, apply migrations and seed data.
2. Start `llama-server`.
3. Start the app with `USE_LLAMA=true`.
4. Send a message in `/chat/`.
5. Check the `generated_responses` table:
   - `source = local_llama_cpp` means llama.cpp answered.
   - `source = local_rules` means fallback answered.
