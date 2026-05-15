from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import Category, KnowledgeBaseItem


CATEGORIES = [
    ("service-cost", "service cost", "Questions about service pricing and budgeting."),
    ("campaign-launch", "campaign launch", "Requests about starting a new advertising campaign."),
    ("low-number-of-leads", "low number of leads", "Requests about insufficient lead volume."),
    (
        "dissatisfaction-with-campaign-results",
        "dissatisfaction with campaign results",
        "Negative feedback about advertising results.",
    ),
    ("limited-budget", "limited budget", "Requests with strict budget limitations."),
    ("consultation-request", "consultation request", "Requests for an expert consultation."),
    ("contact-manager-request", "contact manager request", "Requests to speak with a human manager."),
    ("general-question", "general question", "General questions about agency services."),
    ("other", "other", "Requests that do not match prepared categories."),
]

COMMENTS = {
    "service-cost": [
        (
            "Ask for scope before price",
            "Стоимость зависит от целей, региона, рекламных каналов и объема работ. Менеджер может подготовить расчет после уточнения задачи.",
            10,
        ),
        (
            "No fixed promise",
            "Не называйте точную цену без вводных данных. Сначала уточните нишу, желаемые каналы продвижения и ориентировочный бюджет.",
            20,
        ),
    ],
    "campaign-launch": [
        (
            "Launch inputs",
            "Для запуска кампании нужно уточнить продукт, целевую аудиторию, регион, посадочную страницу и желаемый срок старта.",
            10,
        ),
        (
            "Manager next step",
            "Менеджер может предложить план подготовки после короткого брифа и проверки исходных материалов клиента.",
            20,
        ),
    ],
    "low-number-of-leads": [
        (
            "Lead diagnosis",
            "При низком количестве заявок важно проверить период статистики, бюджет, настройки аудитории, посадочную страницу и качество оффера.",
            10,
        ),
        (
            "Request data",
            "Попросите клиента прислать период кампании, рекламный канал и текущие показатели, чтобы менеджер мог оценить ситуацию предметно.",
            20,
        ),
    ],
    "dissatisfaction-with-campaign-results": [
        (
            "Acknowledge concern",
            "Сначала подтвердите, что обеспокоенность клиента понятна, затем предложите разобрать показатели и историю изменений кампании.",
            10,
        ),
        (
            "Human review",
            "Если обращение эмоциональное или негативное, предложите передать диалог менеджеру с сохранением контекста.",
            15,
        ),
    ],
    "limited-budget": [
        (
            "Budget constraints",
            "При ограниченном бюджете нужно выбрать приоритетную цель и канал, чтобы не распылять средства на слишком широкий запуск.",
            10,
        ),
        (
            "Clarify priorities",
            "Уточните минимальный комфортный бюджет, регион и ключевое действие: заявка, звонок, подписка или продажа.",
            20,
        ),
    ],
    "consultation-request": [
        (
            "Consultation details",
            "Для консультации стоит уточнить нишу, текущую задачу, рекламные каналы и удобный способ связи.",
            10,
        ),
    ],
    "contact-manager-request": [
        (
            "Transfer to manager",
            "Если клиент просит менеджера, подтвердите передачу обращения и сохраните краткий контекст запроса.",
            10,
        ),
    ],
    "general-question": [
        (
            "General answer boundary",
            "Ответ должен быть спокойным и информативным, без обещаний сроков, цен или гарантированных результатов.",
            10,
        ),
    ],
    "other": [
        (
            "Clarifying question",
            "Если категория не определена, задайте один-два уточняющих вопроса и предложите помощь менеджера.",
            10,
        ),
    ],
}


def upsert_categories(db: Session) -> dict[str, Category]:
    categories: dict[str, Category] = {}
    for slug, name, description in CATEGORIES:
        category = db.scalar(select(Category).where(Category.slug == slug))
        if category is None:
            category = Category(slug=slug, name=name, description=description)
            db.add(category)
        else:
            category.name = name
            category.description = description
            category.is_active = True
        categories[slug] = category

    db.flush()
    return categories


def upsert_comments(db: Session, categories: dict[str, Category]) -> None:
    for slug, comments in COMMENTS.items():
        category = categories[slug]
        for title, content, priority in comments:
            item = db.scalar(
                select(KnowledgeBaseItem).where(
                    KnowledgeBaseItem.category_id == category.id,
                    KnowledgeBaseItem.title == title,
                )
            )
            if item is None:
                item = KnowledgeBaseItem(
                    category_id=category.id,
                    title=title,
                    content=content,
                    priority=priority,
                )
                db.add(item)
            else:
                item.content = content
                item.priority = priority
                item.is_active = True


def seed() -> None:
    with SessionLocal() as db:
        categories = upsert_categories(db)
        upsert_comments(db, categories)
        db.commit()


if __name__ == "__main__":
    seed()
    print("Seed data has been loaded.")
