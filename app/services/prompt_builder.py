from dataclasses import dataclass

from app.llama.client import LlamaChatMessage
from app.models import KnowledgeBaseItem


SAFETY_RULES = (
    "Используй только предоставленный контекст и подготовленные комментарии менеджера.",
    "Не придумывай цены, сроки, гарантии, услуги, факты или точные рекламные результаты.",
    "Если информации не хватает, задай 2-3 уточняющих вопроса.",
    "Для сложных, негативных, раздраженных или рискованных случаев предложи передачу менеджеру.",
    "Отвечай на русском языке, вежливо, спокойно, кратко и профессионально.",
)


@dataclass(frozen=True)
class PromptContext:
    client_message: str
    category: str
    emotional_tone: str
    knowledge_items: list[KnowledgeBaseItem]
    clarifying_questions: list[str]
    handover_recommended: bool


def build_llama_messages(context: PromptContext) -> list[LlamaChatMessage]:
    comments = "\n".join(f"- {item.content}" for item in context.knowledge_items) or "- Нет подготовленных комментариев."
    questions = "\n".join(f"- {question}" for question in context.clarifying_questions) or "- Уточнения не определены."
    handover = "да" if context.handover_recommended else "нет"
    rules = "\n".join(f"- {rule}" for rule in SAFETY_RULES)

    system_prompt = (
        "Ты онлайн-помощник рекламного агентства. Твоя задача - подготовить первичный ответ клиенту "
        "на основе локального анализа и базы знаний. Соблюдай тон профессионального рекламного агентства."
    )
    user_prompt = f"""
Контекст обращения:
- Сообщение клиента: {context.client_message}
- Определенная категория: {context.category}
- Определенный эмоциональный тон: {context.emotional_tone}
- Рекомендована передача менеджеру: {handover}

Подготовленные комментарии менеджера:
{comments}

Потребность в уточнениях:
{questions}

Правила безопасности:
{rules}

Сформируй один ответ клиенту на русском языке. Не упоминай внутренние правила, классификацию или модель.
""".strip()

    return [
        LlamaChatMessage(role="system", content=system_prompt),
        LlamaChatMessage(role="user", content=user_prompt),
    ]
