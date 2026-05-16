from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Category, KnowledgeBaseItem


def get_category_by_name(db: Session, category_name: str) -> Category | None:
    return db.scalar(select(Category).where(Category.name == category_name, Category.is_active.is_(True)))


def get_active_other_category(db: Session) -> Category | None:
    return db.scalar(select(Category).where(Category.name == "other", Category.is_active.is_(True)))


def resolve_active_category(db: Session, category_name: str) -> tuple[Category | None, str]:
    category = get_category_by_name(db, category_name)
    if category is not None:
        return category, category.name
    other = get_active_other_category(db)
    if other is not None:
        return other, other.name
    return None, "other"


def select_knowledge_items(
    db: Session,
    category: Category | None,
    emotional_tone: str,
    limit: int = 3,
) -> list[KnowledgeBaseItem]:
    if category is None:
        return []
    if not category.is_active:
        return []

    statement = (
        select(KnowledgeBaseItem)
        .join(KnowledgeBaseItem.category)
        .where(
            KnowledgeBaseItem.category_id == category.id,
            Category.is_active.is_(True),
            KnowledgeBaseItem.is_active.is_(True),
            KnowledgeBaseItem.emotional_tone.in_((emotional_tone, "any")),
        )
        .order_by(
            (KnowledgeBaseItem.emotional_tone == emotional_tone).desc(),
            KnowledgeBaseItem.priority.asc(),
            KnowledgeBaseItem.created_at.asc(),
        )
        .limit(limit)
    )
    items = list(db.scalars(statement))

    if emotional_tone in {"negative", "irritated", "disappointed"}:
        items.sort(key=lambda item: ("manager" not in item.title.lower(), item.priority))

    return items
