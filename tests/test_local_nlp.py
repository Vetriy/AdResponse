from types import SimpleNamespace

from app.services.classification import classify_request
from app.services.response_generation import build_clarifying_questions, generate_fallback_response
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
    assert "Уточните нишу" in result.text
    assert "Чтобы продолжить" in result.text


def test_fallback_response_offers_handover_for_negative_request() -> None:
    result = generate_fallback_response(
        text="Мы недовольны, плохой результат кампании",
        category="dissatisfaction with campaign results",
        emotional_tone="disappointed",
        knowledge_items=[],
    )

    assert result.handover_offered is True
    assert "Понимаем ваше беспокойство" in result.text
    assert "передать диалог менеджеру" in result.text
