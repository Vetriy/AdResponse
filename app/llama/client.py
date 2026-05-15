from dataclasses import dataclass
from urllib.parse import urlparse

import httpx


class LlamaClientError(RuntimeError):
    pass


@dataclass(frozen=True)
class LlamaChatMessage:
    role: str
    content: str


class LlamaCppClient:
    def __init__(self, endpoint_url: str, model_name: str, timeout_seconds: float) -> None:
        self.endpoint_url = endpoint_url
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds
        self._validate_local_endpoint()

    def _validate_local_endpoint(self) -> None:
        parsed = urlparse(self.endpoint_url)
        if parsed.scheme not in {"http", "https"}:
            raise LlamaClientError("llama.cpp endpoint must use HTTP.")
        if parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
            raise LlamaClientError("llama.cpp endpoint must be local only.")
        if parsed.path.rstrip("/") != "/v1/chat/completions":
            raise LlamaClientError("llama.cpp endpoint must be /v1/chat/completions.")

    def chat(self, messages: list[LlamaChatMessage]) -> str:
        payload = {
            "model": self.model_name,
            "messages": [{"role": message.role, "content": message.content} for message in messages],
            "temperature": 0.2,
            "stream": False,
        }

        try:
            response = httpx.post(self.endpoint_url, json=payload, timeout=self.timeout_seconds)
            response.raise_for_status()
            data = response.json()
        except httpx.TimeoutException as error:
            raise LlamaClientError("llama.cpp request timed out.") from error
        except httpx.HTTPError as error:
            raise LlamaClientError("llama.cpp is not available.") from error
        except ValueError as error:
            raise LlamaClientError("llama.cpp returned invalid JSON.") from error

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise LlamaClientError("llama.cpp returned an unexpected response shape.") from error

        if not isinstance(content, str) or not content.strip():
            raise LlamaClientError("llama.cpp returned an empty response.")

        return content.strip()
