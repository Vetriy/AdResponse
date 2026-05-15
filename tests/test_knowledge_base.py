from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import Category, KnowledgeBaseItem
from app.services.knowledge_base import select_knowledge_items


def test_knowledge_base_selection_uses_category_tone_active_flag_and_priority() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        category = Category(slug="service-cost", name="service cost", is_active=True)
        other_category = Category(slug="other", name="other", is_active=True)
        db.add_all([category, other_category])
        db.flush()
        db.add_all(
            [
                KnowledgeBaseItem(
                    category_id=category.id,
                    emotional_tone="any",
                    title="General comment",
                    content="General",
                    priority=20,
                    is_active=True,
                ),
                KnowledgeBaseItem(
                    category_id=category.id,
                    emotional_tone="negative",
                    title="Negative tone comment",
                    content="Negative",
                    priority=10,
                    is_active=True,
                ),
                KnowledgeBaseItem(
                    category_id=category.id,
                    emotional_tone="negative",
                    title="Inactive comment",
                    content="Inactive",
                    priority=1,
                    is_active=False,
                ),
                KnowledgeBaseItem(
                    category_id=other_category.id,
                    emotional_tone="negative",
                    title="Wrong category",
                    content="Wrong",
                    priority=1,
                    is_active=True,
                ),
            ]
        )
        db.commit()

        items = select_knowledge_items(db, category, "negative", limit=5)

    assert [item.content for item in items] == ["Negative", "General"]
