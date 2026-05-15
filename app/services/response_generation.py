from dataclasses import dataclass

from app.core.config import settings
from app.llama.client import LlamaClientError, LlamaCppClient
from app.models import KnowledgeBaseItem
from app.services.prompt_builder import PromptContext, build_llama_messages


@dataclass(frozen=True)
class GeneratedChatResponse:
    text: str
    clarifying_questions: list[str]
    handover_offered: bool
    status: str
    source: str = "local_rules"


MISSING_INFO_QUESTIONS: dict[str, tuple[tuple[str, tuple[str, ...]], ...]] = {
    "service cost": (
        ("Какую услугу или рекламный канал вы рассматриваете?", ("услуг", "канал", "контекст", "таргет")),
        ("В каком регионе планируется продвижение?", ("регион", "город", "область")),
        ("Какой ориентировочный бюджет комфортно рассматривать?", ("бюджет", "руб", "тысяч")),
    ),
    "campaign launch": (
        ("Какой продукт или услугу нужно продвигать?", ("продукт", "услуг", "товар", "ниша")),
        ("В каком регионе и для какой аудитории планируется запуск?", ("регион", "аудитор", "клиент")),
        ("Есть ли уже сайт, лендинг или материалы для рекламы?", ("сайт", "лендинг", "материал")),
    ),
    "low number of leads": (
        ("За какой период вы оцениваете количество заявок?", ("период", "недел", "месяц", "день")),
        ("Какой рекламный канал сейчас используется?", ("канал", "контекст", "таргет", "директ")),
        ("Какие текущие показатели по расходу, кликам и заявкам?", ("расход", "клик", "заяв")),
    ),
    "dissatisfaction with campaign results": (
        ("За какой период виден неудовлетворительный результат?", ("период", "недел", "месяц")),
        ("Какие показатели вызывают основное беспокойство?", ("лид", "заяв", "стоимость", "конвер")),
        ("Были ли недавно изменения в кампании или на сайте?", ("измен", "сайт", "кампан")),
    ),
    "limited budget": (
        ("Какой бюджет является верхней границей на тестовый запуск?", ("бюджет", "руб", "тысяч")),
        ("Какая цель сейчас важнее всего: заявки, звонки или узнаваемость?", ("заяв", "звон", "узнаваем")),
    ),
    "consultation request": (
        ("По какой нише или услуге нужна консультация?", ("ниш", "услуг", "продукт")),
        ("Какой вопрос сейчас самый важный для обсуждения?", ("вопрос", "важн", "обсуд")),
    ),
    "contact manager request": (
        ("Какой способ связи вам удобен?", ("телефон", "почт", "telegram", "связ")),
        ("Кратко опишите задачу, чтобы менеджер сразу видел контекст.", ("задач", "контекст", "вопрос")),
    ),
}


COMPLEX_CATEGORIES = {"low number of leads", "dissatisfaction with campaign results", "contact manager request"}
NEGATIVE_TONES = {"negative", "irritated", "disappointed"}


def build_clarifying_questions(text: str, category: str) -> list[str]:
    normalized = text.lower()
    checks = MISSING_INFO_QUESTIONS.get(category, ())
    questions = [
        question
        for question, keywords in checks
        if not any(keyword in normalized for keyword in keywords)
    ]
    return questions[:3]


def generate_fallback_response(
    text: str,
    category: str,
    emotional_tone: str,
    knowledge_items: list[KnowledgeBaseItem],
) -> GeneratedChatResponse:
    questions = build_clarifying_questions(text, category)
    handover_offered = category in COMPLEX_CATEGORIES or emotional_tone in NEGATIVE_TONES
    parts: list[str] = []

    if emotional_tone in NEGATIVE_TONES:
        parts.append(
            "Понимаем ваше беспокойство. Давайте спокойно разберем ситуацию по фактам и сохраним контекст обращения для менеджера."
        )
    else:
        parts.append("Спасибо за обращение. Мы зафиксировали ваш запрос и можем подготовить первичный ответ по имеющимся данным.")

    if knowledge_items:
        parts.append("По вашему обращению можем сориентировать так:")
        parts.extend(f"- {item.content}" for item in knowledge_items[:2])
    else:
        parts.append(
            "Для точного ответа нужно немного больше вводных. Мы не называем цены, сроки или гарантии без подтвержденных данных."
        )

    if questions:
        parts.append("Чтобы продолжить, уточните, пожалуйста:")
        parts.extend(f"{index}. {question}" for index, question in enumerate(questions, start=1))

    if handover_offered:
        if category == "contact manager request":
            parts.append("Мы можем передать обращение менеджеру. Если удобно, укажите способ связи и краткий контекст задачи.")
        else:
            parts.append("Если вопрос требует детального разбора, мы можем передать диалог менеджеру с сохранением истории.")

    return GeneratedChatResponse(
        text="\n".join(parts),
        clarifying_questions=questions,
        handover_offered=handover_offered,
        status="needs_clarification" if questions else "draft",
        source="local_rules",
    )


def generate_chat_response(
    text: str,
    category: str,
    emotional_tone: str,
    knowledge_items: list[KnowledgeBaseItem],
    llama_client: LlamaCppClient | None = None,
) -> GeneratedChatResponse:
    fallback = generate_fallback_response(text, category, emotional_tone, knowledge_items)

    if not settings.use_llama:
        return fallback

    try:
        client = llama_client or LlamaCppClient(
            endpoint_url=settings.llama_base_url,
            model_name=settings.llama_model_name,
            timeout_seconds=settings.llama_timeout_seconds,
        )
        messages = build_llama_messages(
            PromptContext(
                client_message=text,
                category=category,
                emotional_tone=emotional_tone,
                knowledge_items=knowledge_items,
                clarifying_questions=fallback.clarifying_questions,
                handover_recommended=fallback.handover_offered,
            )
        )
        llama_text = client.chat(messages)
    except LlamaClientError:
        return fallback

    return GeneratedChatResponse(
        text=llama_text,
        clarifying_questions=fallback.clarifying_questions,
        handover_offered=fallback.handover_offered,
        status=fallback.status,
        source="local_llama_cpp",
    )
