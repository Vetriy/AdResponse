from dataclasses import dataclass

from app.core.config import settings
from app.llama.client import LlamaClientError, LlamaCppClient
from app.models import KnowledgeBaseItem, Message
from app.services.prompt_builder import PromptContext, build_llama_messages


@dataclass(frozen=True)
class GeneratedChatResponse:
    text: str
    clarifying_questions: list[str]
    handover_offered: bool
    status: str
    source: str = "local_rules"


@dataclass(frozen=True)
class DialogueContext:
    latest_client_message: str
    previous_client_messages: tuple[str, ...] = ()
    previous_system_messages: tuple[str, ...] = ()
    previous_manager_messages: tuple[str, ...] = ()
    report_context: str | None = None

    @property
    def all_text(self) -> str:
        parts = [
            *self.previous_client_messages,
            *self.previous_system_messages,
            *self.previous_manager_messages,
            self.latest_client_message,
        ]
        if self.report_context:
            parts.append(self.report_context)
        return "\n".join(part for part in parts if part)


def build_dialogue_context(
    latest_client_message: str,
    messages: list[Message] | tuple[Message, ...] | None = None,
    report_context: str | None = None,
) -> DialogueContext:
    previous_client_messages: list[str] = []
    previous_system_messages: list[str] = []
    previous_manager_messages: list[str] = []

    for message in messages or ():
        if message.sender_type == "client":
            previous_client_messages.append(message.content)
        elif message.sender_type == "system":
            previous_system_messages.append(message.content)
        elif message.sender_type == "manager":
            previous_manager_messages.append(message.content)

    return DialogueContext(
        latest_client_message=latest_client_message,
        previous_client_messages=tuple(previous_client_messages[-6:]),
        previous_system_messages=tuple(previous_system_messages[-4:]),
        previous_manager_messages=tuple(previous_manager_messages[-4:]),
        report_context=report_context,
    )


MISSING_INFO_QUESTIONS: dict[str, tuple[tuple[str, tuple[str, ...]], ...]] = {
    "service cost": (
        ("Какую услугу или рекламный канал вы рассматриваете?", ("услуг", "канал", "контекст", "таргет", "продвиг", "салон", "клиник")),
        ("В каком регионе планируется продвижение?", ("регион", "город", "область", "москв", "спб", "санкт")),
        ("Какой ориентировочный бюджетный диапазон комфортно рассматривать?", ("бюджет", "руб", "тысяч", "млн", "миллион")),
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
    "other": (
        ("Какую услугу, продукт или направление нужно продвигать?", ("услуг", "продукт", "направлен", "клиник", "салон")),
        ("Какая цель важнее сейчас: заявки, звонки, продажи или узнаваемость?", ("заяв", "звон", "продаж", "узнаваем")),
    ),
}


COMPLEX_CATEGORIES = {"low number of leads", "dissatisfaction with campaign results", "contact manager request"}
NEGATIVE_TONES = {"negative", "irritated", "disappointed"}
PLAYFUL_OFFTOPIC_MARKERS = ("кот", "котик", "собак", "мем", "шутк", "как вам", "нравится")
ADVERTISING_CONTEXT_MARKERS = (
    "реклам",
    "продвиж",
    "заяв",
    "лид",
    "кампан",
    "сайт",
    "лендинг",
    "клиник",
    "стомат",
    "салон",
    "услуг",
    "бюджет",
    "отчет",
    "результат",
    "клик",
    "конверс",
)


def build_clarifying_questions(text: str, category: str, dialogue_context: str | None = None) -> list[str]:
    normalized = f"{text}\n{dialogue_context or ''}".lower()
    checks = MISSING_INFO_QUESTIONS.get(category, ())
    questions = [
        question
        for question, keywords in checks
        if not any(keyword in normalized for keyword in keywords)
    ]
    return questions[:3]


def knowledge_summary_for_client(category: str, emotional_tone: str, knowledge_items: list[KnowledgeBaseItem]) -> str:
    if not knowledge_items:
        return (
            "Точные цены, сроки и прогнозы корректно считать только после уточнения вводных, поэтому сначала соберем недостающие детали."
        )

    if category == "service cost":
        return "Обычно стоимость зависит от ниши, региона, выбранных каналов, объема работ и стартовых материалов."
    if category == "campaign launch":
        return "Для запуска важно собрать вводные по продукту, аудитории, географии, посадочной странице и желаемой дате старта."
    if category in {"low number of leads", "dissatisfaction with campaign results"}:
        return "Для предметного разбора стоит проверить период, каналы, бюджет, посадочную страницу и путь клиента до заявки."
    if category == "limited budget":
        return "При ограниченном бюджете лучше сфокусироваться на одной главной цели и одном приоритетном канале."
    if category == "contact manager request":
        return "Передам запрос так, чтобы менеджер видел задачу и текущую историю диалога."
    if emotional_tone in NEGATIVE_TONES:
        return "Сначала зафиксируем факты и контекст, чтобы менеджер мог быстро перейти к решению."
    return "Опираюсь на внутреннюю базу агентства и перевожу ее в короткий клиентский ответ без служебных формулировок."


def opening_for(category: str, emotional_tone: str, unusual: bool, has_previous_system: bool) -> str:
    if unusual:
        return "Сообщение понял. Отвечу легко: звучит приятно и по-доброму."
    if has_previous_system:
        return "Спасибо, продолжаю по текущему диалогу."
    if category == "service cost":
        return "По стоимости сориентируем аккуратно: цена зависит от нескольких вводных, поэтому точную сумму без них не придумываю."
    if category == "campaign launch":
        return "Запуск можно подготовить по шагам: сначала уточним продукт, аудиторию и готовность материалов."
    if category == "limited budget":
        return "При ограниченном бюджете лучше сразу выбрать главный приоритет, чтобы не распылять запуск."
    if category == "contact manager request":
        return "Передать диалог менеджеру можно."
    if emotional_tone == "anxious":
        return "Ситуацию можно спокойно проверить по шагам: сначала уточним вводные, затем будет проще понять, где нужен разбор."
    if emotional_tone in NEGATIVE_TONES:
        return "Понимаю, что ситуация вызывает недовольство и беспокойство по результатам. Давайте отделим эмоции от фактов, спокойно соберем данные и передадим контекст без потери деталей."
    if emotional_tone == "interested":
        return "Хороший запрос, давайте сразу сузим задачу, чтобы ответ был полезным и без лишних предположений."
    return "Разберем ваш вопрос по делу: для точного ответа важно понять несколько параметров кампании или задачи."


def is_playful_or_unusual(text: str, category: str) -> bool:
    normalized = text.lower()
    return any(marker in normalized for marker in PLAYFUL_OFFTOPIC_MARKERS) or (
        category == "other" and not is_advertising_related(text, category)
    )


def is_advertising_related(text: str, category: str) -> bool:
    if category != "other":
        return True
    normalized = text.lower()
    return any(marker in normalized for marker in ADVERTISING_CONTEXT_MARKERS)


def generate_fallback_response(
    text: str,
    category: str,
    emotional_tone: str,
    knowledge_items: list[KnowledgeBaseItem],
    report_context: str | None = None,
    dialogue_context: DialogueContext | None = None,
) -> GeneratedChatResponse:
    context = dialogue_context or DialogueContext(latest_client_message=text, report_context=report_context)
    context_text = context.all_text
    questions = build_clarifying_questions(text, category, context_text)
    unusual = is_playful_or_unusual(text, category)
    advertising_related = is_advertising_related(text, category)
    if unusual and not questions:
        questions = [
            "Хотите обсудить продвижение, результаты отчета или материалы для рекламной кампании?",
            "Нужно подключить менеджера к вопросу или достаточно краткой консультации здесь?",
        ]
    handover_offered = category in COMPLEX_CATEGORIES or emotional_tone in NEGATIVE_TONES
    parts: list[str] = []

    if unusual:
        parts.append(opening_for(category, emotional_tone, unusual, bool(context.previous_system_messages)))
        parts.append("А по рабочей части могу помочь с продвижением, отчетами, материалами кампании или вопросом для менеджера.")
    elif category == "contact manager request":
        parts.append(opening_for(category, emotional_tone, unusual, bool(context.previous_system_messages)))
        parts.append("Чтобы специалист быстрее включился, достаточно оставить удобный способ связи и коротко обозначить задачу, если этого еще нет в переписке.")
    elif advertising_related and category == "other":
        parts.append(opening_for(category, emotional_tone, unusual, bool(context.previous_system_messages)))
        parts.append("Похоже, вопрос связан с продвижением, но задачи пока мало для точного ответа.")
    else:
        parts.append(opening_for(category, emotional_tone, unusual, bool(context.previous_system_messages)))

    active_report_context = context.report_context or report_context
    if active_report_context:
        parts.append(f"Учитываю контекст отчета: {active_report_context}. Я вижу только название и описание отчета, без автоматического разбора содержимого файла.")

    if not unusual:
        parts.append(knowledge_summary_for_client(category, emotional_tone, knowledge_items))

    if category == "service cost":
        parts.append("Чтобы сориентировать по запуску, важно понять нишу, регион, цель, подходящие каналы и комфортный бюджетный диапазон.")
    elif category == "campaign launch":
        parts.append("После этих вводных можно предложить безопасный первый шаг без обещаний точных результатов заранее.")
    elif category in {"low number of leads", "dissatisfaction with campaign results"}:
        parts.append("Никого не обвиняю: в таких ситуациях часто влияет связка из настроек, бюджета, посадочной страницы и обработки заявок.")
    elif category == "limited budget":
        parts.append("Можно начать с тестового формата, но лучше заранее обозначить верхнюю границу бюджета и главный ожидаемый результат.")

    if questions:
        parts.append("Уточните, пожалуйста:")
        parts.extend(f"{index}. {question}" for index, question in enumerate(questions, start=1))

    if handover_offered:
        if category == "contact manager request":
            parts.append("Укажите удобный способ связи и кратко опишите задачу: так менеджер получит диалог уже с подготовленными вводными.")
        else:
            parts.append("Если нужно, передадим диалог менеджеру с сохранением истории: ему не придется заново собирать контекст.")

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
    report_context: str | None = None,
    dialogue_context: DialogueContext | None = None,
) -> GeneratedChatResponse:
    context = dialogue_context or DialogueContext(latest_client_message=text, report_context=report_context)
    fallback = generate_fallback_response(
        text,
        category,
        emotional_tone,
        knowledge_items,
        report_context=report_context,
        dialogue_context=context,
    )

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
                client_message=f"{text}\n\nКонтекст отчета: {report_context}" if report_context else text,
                dialogue_context=context.all_text,
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
