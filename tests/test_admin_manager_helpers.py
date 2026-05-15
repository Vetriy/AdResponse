from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import User
from app.routers.admin import form_bool, form_int, slugify
from app.routers.manager import PLACEHOLDER_MANAGER_EMAIL, get_or_create_placeholder_manager


def test_admin_form_helpers_are_predictable() -> None:
    assert slugify(" Service Cost ") == "service-cost"
    assert slugify("campaign_launch") == "campaign-launch"
    assert form_bool({"is_active": "true"}, "is_active") is True
    assert form_bool({}, "is_active") is False
    assert form_int({"priority": "15"}, "priority", 100) == 15
    assert form_int({"priority": "bad"}, "priority", 100) == 100


def test_placeholder_manager_is_created_once() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        first = get_or_create_placeholder_manager(db)
        second = get_or_create_placeholder_manager(db)
        users = list(db.scalars(select(User).where(User.email == PLACEHOLDER_MANAGER_EMAIL)))

    assert first.id == second.id
    assert len(users) == 1
    assert users[0].full_name == "Дежурный менеджер"
