from types import SimpleNamespace

from app.services.classification import classify_request
from app.services.response_generation import DialogueContext, build_clarifying_questions, generate_fallback_response
from app.services.sentiment import analyze_sentiment


def test_classification_detects_expected_categories() -> None:
    samples = {
        "Сколько стоит запуск рекламы?": "service cost",
        "Хотим запустить новую рекламную кампанию": "campaign launch",
        "Мало лидов и почти нет заявок": "low number of leads",
        "Недовольны, плохой результат кампании": "dissatisfaction with campaign results",
        "Бюджет ограничен, денег мало": "limited budget",
        "Нужна консультация по продвижению": "consultation request",
        "Хочу поговорить с менеджером": "contact manager request",
        "Расскажите, какие услуги вы делаете": "general question",
    }

    for text, expected_category in samples.items():
        assert classify_request(text).category == expected_category


def test_classification_falls_back_to_other() -> None:
    assert classify_request("Добрый день").category == "other"


def test_sentiment_detects_emotional_tone() -> None:
    assert analyze_sentiment("Хотим узнать подробнее").emotional_tone == "interested"
    assert analyze_sentiment("Переживаем, что реклама не сработает").emotional_tone == "anxious"
    assert analyze_sentiment("Разочарованы, ожидали лучше").emotional_tone == "disappointed"
    assert analyze_sentiment("Сколько можно ждать отчет").emotional_tone == "irritated"
    assert analyze_sentiment("Это ужасно, результата совсем нет").emotional_tone == "negative"
    assert analyze_sentiment("Добрый день").emotional_tone == "neutral"


def test_clarifying_questions_are_limited_and_category_specific() -> None:
    questions = build_clarifying_questions("Сколько стоит реклама?", "service cost")

    assert 1 <= len(questions) <= 3
    assert "регион" in " ".join(questions).lower()


def test_fallback_response_uses_manager_comments_and_safe_rules() -> None:
    item = SimpleNamespace(content="Уточните нишу, регион и ориентировочный бюджет.")

    result = generate_fallback_response(
        text="Сколько стоит реклама?",
        category="service cost",
        emotional_tone="interested",
        knowledge_items=[item],
    )

    assert result.source == "local_rules"
    assert result.handover_offered is False
    assert "Уточните нишу" not in result.text
    assert "стоимость зависит" in result.text
    assert "Уточните, пожалуйста" in result.text
    assert "подготовленных комментариев менеджера" not in result.text.lower()


def test_fallback_response_offers_handover_for_negative_request() -> None:
    result = generate_fallback_response(
        text="Мы недовольны, плохой результат кампании",
        category="dissatisfaction with campaign results",
        emotional_tone="disappointed",
        knowledge_items=[],
    )

    assert result.handover_offered is True
    assert "недовольство" in result.text
    assert "передадим диалог менеджеру" in result.text


def test_dialogue_context_avoids_repeating_answered_questions() -> None:
    context = DialogueContext(
        latest_client_message="Бюджет можем рассматривать до 80 тысяч.",
        previous_client_messages=("Нужна реклама салона красоты в Москве.",),
        previous_system_messages=("Уточните город и бюджет.",),
    )

    result = generate_fallback_response(
        text=context.latest_client_message,
        category="service cost",
        emotional_tone="interested",
        knowledge_items=[],
        dialogue_context=context,
    )
    lowered_questions = " ".join(result.clarifying_questions).lower()

    assert "регион" not in lowered_questions
    assert "бюджет" not in lowered_questions
    assert "услугу" not in lowered_questions


def test_follow_up_response_does_not_start_with_repetitive_template_phrase() -> None:
    context = DialogueContext(
        latest_client_message="Бюджет до 80 тысяч, Москва.",
        previous_client_messages=("Сколько стоит реклама для салона красоты?",),
        previous_system_messages=("Уточните регион и бюджет.",),
    )

    result = generate_fallback_response(
        text=context.latest_client_message,
        category="service cost",
        emotional_tone="interested",
        knowledge_items=[],
        dialogue_context=context,
    )
    lowered = result.text.lower()

    assert not lowered.startswith("спасибо")
    assert "спасибо, продолжаю по текущему диалогу" not in lowered
    assert "спасибо за обращение" not in lowered
    assert "сообщение понял" not in lowered


def test_landing_page_explanation_is_natural_for_follow_up_question() -> None:
    result = generate_fallback_response(
        text="Посадочная страница я не знаю что это такое, объясните",
        category="campaign launch",
        emotional_tone="neutral",
        knowledge_items=[],
        dialogue_context=DialogueContext(
            latest_client_message="Посадочная страница я не знаю что это такое, объясните",
            previous_client_messages=("Хотим запустить рекламу новой услуги в Москве.",),
            previous_system_messages=("Есть ли сайт, лендинг или материалы?",),
        ),
    )
    lowered = result.text.lower()

    assert "страница, куда переходит человек после клика по рекламе" in lowered
    assert "существующий сайт" in lowered
    assert "отдельный лендинг" in lowered
    assert "есть ли уже сайт, лендинг или материалы" not in lowered


def test_missing_landing_page_follow_up_does_not_restart_brief() -> None:
    result = generate_fallback_response(
        text="Посадочной страницы пока нет",
        category="campaign launch",
        emotional_tone="neutral",
        knowledge_items=[],
        dialogue_context=DialogueContext(
            latest_client_message="Посадочной страницы пока нет",
            previous_client_messages=("Продвигаем новую услугу в Москве для владельцев малого бизнеса.",),
        ),
    )
    lowered = result.text.lower()

    assert "существующий сайт" in lowered
    assert "страницу услуги" in lowered
    assert "форму для заявки" in lowered
    assert "какой продукт" not in lowered
    assert "в каком регионе" not in lowered


def test_prepared_comments_are_internal_source_material_only() -> None:
    item = SimpleNamespace(content="Сначала подтвердите проблему, затем попросите период и канал.")

    result = generate_fallback_response(
        text="Мы недовольны результатами, заявок почти нет.",
        category="dissatisfaction with campaign results",
        emotional_tone="disappointed",
        knowledge_items=[item],
    )
    lowered = result.text.lower()

    assert "сначала подтвердите" not in lowered
    assert "попросите период" not in lowered
    assert "период" in lowered
    assert "менеджеру" in lowered


def test_fallback_response_varies_by_emotional_tone() -> None:
    anxious = generate_fallback_response(
        text="Переживаем из-за отчета",
        category="general question",
        emotional_tone="anxious",
        knowledge_items=[],
    )
    negative = generate_fallback_response(
        text="Отчет плохой, заявок нет",
        category="low number of leads",
        emotional_tone="negative",
        knowledge_items=[],
    )

    assert anxious.text != negative.text
    assert "спокойно проверить по шагам" in anxious.text
    assert "отделим эмоции от фактов" in negative.text


def test_unusual_question_fallback_is_human_and_ad_context_safe() -> None:
    result = generate_fallback_response("Как вам котик?", "other", "neutral", [])
    lowered = result.text.lower()

    assert "котик отличный" in lowered
    assert "рекламного креатива" in lowered
    assert "идею для рекламы" in lowered
    assert result.clarifying_questions == []
    for forbidden in ("легкий вопрос", "отвечу коротко", "по-доброму", "по рабочей части"):
        assert forbidden not in lowered
    for forbidden in ("prepared", "fallback", "llama", "local_rules", "prompt", "подготовленные комментарии"):
        assert forbidden not in lowered


def test_playful_cat_message_gently_connects_to_advertising_without_meta_phrases() -> None:
    result = generate_fallback_response(
        "Как вам котик?",
        "other",
        "neutral",
        [],
        dialogue_context=DialogueContext(
            latest_client_message="Как вам котик?",
            previous_client_messages=("Нужны идеи для продвижения салона.",),
        ),
    )
    lowered = result.text.lower()

    assert "рекламного креатива" in lowered
    assert "идею для рекламы" in lowered
    assert "легкий вопрос" not in lowered
    assert "отвечу коротко" not in lowered
    assert "по рабочей части" not in lowered


def test_dental_clinic_advertising_request_is_not_treated_as_offtopic() -> None:
    result = generate_fallback_response(
        "Нужна реклама для стоматологической клиники, сколько стоит продвижение?",
        "service cost",
        "neutral",
        [],
    )
    lowered = result.text.lower()

    assert "если вопрос не про рекламу" not in lowered
    assert "продвиж" in lowered or "реклам" in lowered
    assert result.clarifying_questions


def test_new_chat_without_report_context_does_not_mention_report() -> None:
    result = generate_fallback_response(
        "Хотим запустить рекламу для стоматологической клиники",
        "campaign launch",
        "neutral",
        [],
        report_context=None,
    )

    assert "вопрос связан с отчетом" not in result.text.lower()


def test_report_thread_response_uses_report_title_without_claiming_file_parsing() -> None:
    result = generate_fallback_response(
        "Почему в отчете мало заявок?",
        "low number of leads",
        "neutral",
        [],
        report_context="Отчет за май: лидов стало меньше",
    )
    lowered = result.text.lower()

    assert "отчет за май" in lowered
    assert "название и описание" in lowered
    assert "разбора содержимого файла" in lowered
    assert "прочитал файл" not in lowered


def test_client_response_does_not_expose_internal_phrases() -> None:
    result = generate_fallback_response(
        "Сколько стоит реклама для салона?",
        "service cost",
        "neutral",
        [],
    )
    lowered = result.text.lower()

    for forbidden in (
        "fallback",
        "llama.cpp",
        "local_rules",
        "prompt",
        "подготовленные комментарии менеджера",
        "на основе подготовленных комментариев",
        "менеджер может",
        "сначала подтвердите",
        "легкий вопрос",
        "отвечу коротко",
        "по-доброму",
        "по рабочей части",
        "продолжаю по текущему диалогу",
        "сообщение понял",
        "спасибо за обращение",
    ):
        assert forbidden not in lowered
