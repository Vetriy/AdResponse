from types import SimpleNamespace

from app.llama.client import LlamaClientError, LlamaCppClient
from app.services import response_generation
from app.services.prompt_builder import PromptContext, build_llama_messages


def test_prompt_builder_contains_required_context() -> None:
    item = SimpleNamespace(content="Уточните нишу, регион и бюджет перед расчетом.")
    messages = build_llama_messages(
        PromptContext(
            client_message="Сколько стоит реклама?",
            category="service cost",
            emotional_tone="interested",
            knowledge_items=[item],
            clarifying_questions=["В каком регионе планируется продвижение?"],
            handover_recommended=False,
        )
    )

    prompt_text = "\n".join(message.content for message in messages)

    assert "онлайн-помощник рекламного агентства" in prompt_text
    assert "Сколько стоит реклама?" in prompt_text
    assert "service cost" in prompt_text
    assert "interested" in prompt_text
    assert "Уточните нишу" in prompt_text
    assert "Не придумывай цены" in prompt_text


def test_llama_failure_uses_local_fallback(monkeypatch) -> None:
    class FailingLlamaClient:
        def chat(self, messages):
            raise LlamaClientError("not running")

    monkeypatch.setattr(
        response_generation,
        "settings",
        SimpleNamespace(
            use_llama=True,
            llama_base_url="http://localhost:8080/v1/chat/completions",
            llama_model_name="local-model",
            llama_timeout_seconds=1,
        ),
    )

    result = response_generation.generate_chat_response(
        text="Мало лидов, результат не устраивает",
        category="low number of leads",
        emotional_tone="disappointed",
        knowledge_items=[],
        llama_client=FailingLlamaClient(),
    )

    assert result.source == "local_rules"
    assert result.handover_offered is True
    assert "можем передать диалог менеджеру" in result.text


def test_llama_success_uses_local_llama_source(monkeypatch) -> None:
    class WorkingLlamaClient:
        def chat(self, messages):
            return "Здравствуйте! Уточните, пожалуйста, регион, нишу и бюджет."

    monkeypatch.setattr(
        response_generation,
        "settings",
        SimpleNamespace(
            use_llama=True,
            llama_base_url="http://localhost:8080/v1/chat/completions",
            llama_model_name="local-model",
            llama_timeout_seconds=1,
        ),
    )

    result = response_generation.generate_chat_response(
        text="Хочу запустить рекламу",
        category="campaign launch",
        emotional_tone="interested",
        knowledge_items=[],
        llama_client=WorkingLlamaClient(),
    )

    assert result.source == "local_llama_cpp"
    assert result.text == "Здравствуйте! Уточните, пожалуйста, регион, нишу и бюджет."


def test_llama_client_rejects_non_local_endpoint() -> None:
    try:
        LlamaCppClient(
            endpoint_url="https://example.com/v1/chat/completions",
            model_name="model",
            timeout_seconds=1,
        )
    except LlamaClientError as error:
        assert "local only" in str(error)
    else:
        raise AssertionError("Expected non-local llama endpoint to be rejected.")
