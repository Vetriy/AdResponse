from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import Appeal, AppealFeedback, Category, ClientSession, Conversation, Message, User
from app.services.analytics import build_admin_analytics, grouped_appeal_status, percent
from app.services.feedback import manager_rating_summary, normalize_ai_feedback, store_or_update_ai_feedback
from app.services.manager_workflow import (
    assignment_group,
    finish_appeal_for_manager,
    group_manager_appeals,
    resolve_appeal_client,
)
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


def test_report_upload_client_resolution_uses_appeal_session_user() -> None:
    user = User(username="client", email="client@test.local", full_name="Клиент", role="client", hashed_password="x")
    appeal = Appeal(conversation=Conversation(client_session=ClientSession(user=user)))

    assert resolve_appeal_client(appeal) is user


def test_finish_appeal_assigns_manager_and_closes() -> None:
    manager = User(id=7, username="manager", email="m@test.local", full_name="Менеджер", role="manager", hashed_password="x")
    appeal = Appeal(status="assigned_to_manager")

    assert finish_appeal_for_manager(appeal, manager) is True
    assert appeal.status == "closed"
    assert appeal.assigned_manager_id == 7


def test_manager_rating_summary_counts_rated_completed_appeals() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        manager = User(username="manager", email="m@test.local", full_name="Менеджер", role="manager", hashed_password="x")
        client = User(username="client", email="c@test.local", full_name="Клиент", role="client", hashed_password="x")
        appeal = Appeal(conversation=Conversation(client_session=ClientSession(user=client)), status="closed", assigned_manager=manager)
        db.add_all([manager, client, appeal])
        db.flush()
        db.add(AppealFeedback(appeal=appeal, client=client, manager=manager, rating=5))
        db.commit()

        summary = manager_rating_summary(db, manager.id)

    assert summary.average_rating == 5.0
    assert summary.rated_count == 1


def test_ai_feedback_helper_validates_dislike_reason_and_updates() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        client = User(username="client", email="c@test.local", full_name="Клиент", role="client", hashed_password="x")
        conversation = Conversation(client_session=ClientSession(user=client))
        appeal = Appeal(conversation=conversation)
        message = Message(conversation=conversation, sender_type="system", content="Ответ")
        db.add_all([client, conversation, appeal, message])
        db.flush()

        like = store_or_update_ai_feedback(db, message_id=message.id, appeal_id=appeal.id, client_user_id=client.id, value="like")
        db.flush()
        dislike = store_or_update_ai_feedback(
            db,
            message_id=message.id,
            appeal_id=appeal.id,
            client_user_id=client.id,
            value="dislike",
            reason="too_general",
        )

    assert like.id == dislike.id
    assert dislike.value == "dislike"
    assert dislike.reason == "too_general"
    assert normalize_ai_feedback("like", "other", "text") == ("like", None, None)


def test_manager_dashboard_grouping_and_latest_client_activity() -> None:
    assigned_manager_id = 10
    other_manager_id = 20
    appeals = [
        Appeal(id=1, status="new", conversation=Conversation(messages=[Message(sender_type="client", content="1")])),
        Appeal(id=2, status="manager_answered", assigned_manager_id=assigned_manager_id, conversation=Conversation(messages=[Message(sender_type="client", content="2")])),
        Appeal(id=3, status="assigned_to_manager", assigned_manager_id=other_manager_id, conversation=Conversation(messages=[Message(sender_type="client", content="3")])),
        Appeal(id=4, status="closed", assigned_manager_id=assigned_manager_id, conversation=Conversation(messages=[Message(sender_type="client", content="4")])),
    ]

    groups = group_manager_appeals(appeals, assigned_manager_id)

    assert assignment_group(appeals[0], assigned_manager_id) == "unassigned"
    assert groups["mine"] == [appeals[1]]
    assert groups["other"] == [appeals[2]]
    assert groups["completed"] == [appeals[3]]


def test_admin_analytics_groups_totals() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        db.add_all(
            [
                User(username="client", email="c@test.local", full_name="Клиент", role="client", hashed_password="x"),
                User(username="manager", email="m@test.local", full_name="Менеджер", role="manager", hashed_password="x"),
                Category(slug="general", name="general question"),
                Appeal(status="new", conversation=Conversation(client_session=ClientSession())),
                Appeal(status="closed", conversation=Conversation(client_session=ClientSession())),
            ]
        )
        db.commit()

        analytics = build_admin_analytics(db)

    assert percent(1, 4) == 25
    assert grouped_appeal_status("needs_manager") == "manager_needed"
    assert analytics["users"]["total"] == 2
    assert analytics["appeals"]["groups"]["new"] == 1
    assert analytics["appeals"]["groups"]["closed"] == 1
