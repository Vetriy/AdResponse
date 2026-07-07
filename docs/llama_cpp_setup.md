# llama.cpp Setup

## Purpose

The project can work without `llama.cpp`. When `USE_LLAMA=false`, it uses deterministic fallback generation. When `USE_LLAMA=true`, it sends context to a local OpenAI-compatible `llama.cpp` endpoint.

Fine-tuning is not done by `llama.cpp`. The project uses HuggingFace Transformers + PEFT/LoRA for adapting `Qwen/Qwen2.5-1.5B-Instruct`, then uses `llama.cpp` only for local inference of the prepared GGUF model.

## Required endpoint

```text
http://localhost:8080/v1
```

The adapter rejects non-local endpoints and sends chat requests to `/v1/chat/completions`. For backward compatibility, the full `http://localhost:8080/v1/chat/completions` endpoint is also accepted.

## Environment

```env
USE_LLAMA=true
LLAMA_BASE_URL=http://localhost:8080/v1
LLAMA_MODEL_NAME=qwen2.5-adresponse
LLAMA_TIMEOUT_SECONDS=60
```

## Example local server command

The exact binary name depends on how `llama.cpp` was built. A typical local command is:

```bash
./llama-server -m /path/to/qwen2.5-adresponse-q4_k_m.gguf --host 127.0.0.1 --port 8080
```

Model files are not included and should not be downloaded by the application.

## Run application with llama.cpp

```bash
source .venv/bin/activate
export USE_LLAMA=true
export LLAMA_BASE_URL=http://localhost:8080/v1
export LLAMA_MODEL_NAME=qwen2.5-adresponse
export LLAMA_TIMEOUT_SECONDS=60
uvicorn app.main:app --reload
```

## Fine-tuned model

The target model for the thesis pipeline is `Qwen/Qwen2.5-1.5B-Instruct`. Dataset preparation, LoRA/QLoRA training, adapter merge and GGUF conversion are documented in:

```text
ml/finetune_llm/README.md
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
