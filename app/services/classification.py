from dataclasses import dataclass


@dataclass(frozen=True)
class ClassificationResult:
    category: str
    scores: dict[str, int]


CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "service cost": (
        "стоимость",
        "цена",
        "прайс",
        "сколько стоит",
        "бюджет на рекламу",
        "расчет",
        "смета",
        "оплата",
        "тариф",
    ),
    "campaign launch": (
        "запустить",
        "запуск",
        "старт",
        "новая кампания",
        "реклама",
        "продвижение",
        "лиды",
        "заявки",
        "настроить кампанию",
    ),
    "low number of leads": (
        "мало лидов",
        "мало заявок",
        "нет заявок",
        "лиды не идут",
        "низкая конверсия",
        "мало обращений",
        "заявок стало меньше",
    ),
    "dissatisfaction with campaign results": (
        "плохой результат",
        "не устраивает",
        "недовольны",
        "потратили",
        "результата нет",
        "кампания не работает",
        "не окупается",
    ),
    "limited budget": (
        "маленький бюджет",
        "ограниченный бюджет",
        "бюджет ограничен",
        "дешево",
        "минимальный бюджет",
        "денег мало",
    ),
    "consultation request": (
        "консультация",
        "проконсультируйте",
        "посоветовать",
        "обсудить",
        "нужен совет",
        "помогите выбрать",
    ),
    "contact manager request": (
        "менеджер",
        "связаться",
        "позвоните",
        "звонок",
        "человек",
        "оператор",
        "хочу поговорить",
    ),
    "general question": (
        "как работает",
        "расскажите",
        "какие услуги",
        "что вы делаете",
        "информация",
        "вопрос",
    ),
}


def classify_request(text: str) -> ClassificationResult:
    normalized = text.lower()
    scores = {
        category: sum(1 for keyword in keywords if keyword in normalized)
        for category, keywords in CATEGORY_KEYWORDS.items()
    }
    best_category, best_score = max(scores.items(), key=lambda item: item[1])

    if best_score == 0:
        return ClassificationResult(category="other", scores=scores)

    return ClassificationResult(category=best_category, scores=scores)
