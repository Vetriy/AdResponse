from dataclasses import dataclass


@dataclass(frozen=True)
class SentimentResult:
    emotional_tone: str
    confidence: float
    explanation: str


TONE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "negative": ("ужасно", "обман", "верните деньги", "бесполезно", "катастрофа", "совсем плохо"),
    "irritated": ("сколько можно", "надоело", "раздражает", "срочно", "почему до сих пор", "возмущены"),
    "disappointed": ("разочарованы", "ожидали лучше", "не оправдало", "не устраивает", "плохой результат"),
    "anxious": ("переживаем", "боюсь", "опасаемся", "риск", "не уверены", "волнуемся"),
    "interested": ("интересует", "хотим", "планируем", "подскажите", "расскажите", "можно ли"),
}


def analyze_sentiment(text: str) -> SentimentResult:
    normalized = text.lower()
    scores = {
        tone: sum(1 for keyword in keywords if keyword in normalized)
        for tone, keywords in TONE_KEYWORDS.items()
    }
    best_tone, best_score = max(scores.items(), key=lambda item: item[1])

    if best_score == 0:
        return SentimentResult(
            emotional_tone="neutral",
            confidence=0.55,
            explanation="No emotional keywords were detected.",
        )

    confidence = min(0.95, 0.55 + best_score * 0.15)
    return SentimentResult(
        emotional_tone=best_tone,
        confidence=confidence,
        explanation=f"Matched {best_score} local keyword rule(s) for {best_tone}.",
    )
