from datetime import datetime

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import AdvertisingReport, Appeal, AppealFeedback, Category, ClientSession, Conversation, GeneratedResponse, KnowledgeBaseItem, Message, User
from app.services.analytics import build_admin_analytics, grouped_appeal_status, percent
from app.services.feedback import manager_rating_rows, manager_rating_summary, normalize_ai_feedback, store_or_update_ai_feedback
from app.services.labels import client_type_label, latest_generated_response, source_label
from app.services.manager_workflow import (
    actionable_manager_unread_count,
    assignment_group,
    change_client_type,
    client_type_sort_key,
    finish_appeal_for_manager,
    get_or_create_report_conversation,
    group_manager_appeals,
    list_admin_report_conversations,
    mark_conversation_read,
    resolve_appeal_client,
    unread_messages_count,
)
from app.routers.admin import (
    apply_user_filters,
    can_archive_user,
    category_delete_error,
    delete_knowledge_item,
    filter_knowledge_items,
    form_bool,
    form_int,
    slugify,
    toggle_category_active,
)
from app.routers.manager import PLACEHOLDER_MANAGER_EMAIL, get_or_create_placeholder_manager


def test_admin_form_helpers_are_predictable() -> None:
    assert slugify(" Service Cost ") == "service-cost"
    assert slugify("campaign_launch") == "campaign-launch"
    assert form_bool({"is_active": "true"}, "is_active") is True
    assert form_bool({}, "is_active") is False
    assert form_int({"priority": "15"}, "priority", 100) == 15
    assert form_int({"priority": "bad"}, "priority", 100) == 100
    assert client_type_label("active_client") == "Действующий клиент"
    assert client_type_label("potential_client") == "Потенциальный клиент"


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


def test_report_thread_is_persistent_for_active_client_and_unread_counts_work() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        client = User(
            username="client",
            email="c@test.local",
            full_name="Клиент",
            role="client",
            client_type="active_client",
            hashed_password="x",
        )
        db.add(client)
        db.flush()

        first = get_or_create_report_conversation(db, client)
        second = get_or_create_report_conversation(db, client)
        db.add(Message(conversation=first, sender_type="manager", content="Отчет загружен"))
        db.flush()

        assert first.id == second.id
        assert first.conversation_type == "report_thread"
        assert unread_messages_count(first, "client") == 1

        mark_conversation_read(first, "client")
        db.flush()

        assert unread_messages_count(first, "client") == 0


def test_admin_report_conversation_rows_include_report_threads_only() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        client = User(
            username="client",
            email="c@test.local",
            full_name="Клиент",
            role="client",
            client_type="active_client",
            hashed_password="x",
        )
        manager = User(username="manager", email="m@test.local", full_name="Менеджер", role="manager", hashed_password="x")
        regular = Conversation(client_session=ClientSession(user=client), conversation_type="appeal", title="Обычное обращение")
        report = Conversation(client_session=ClientSession(user=client), conversation_type="report_thread", title="Отчеты по рекламе")
        db.add_all([client, manager, regular, report])
        db.flush()
        db.add_all(
            [
                Appeal(conversation=regular),
                Message(conversation=report, sender_type="client", content="Вопрос по отчету"),
                AdvertisingReport(
                    client_user_id=client.id,
                    conversation_id=report.id,
                    uploaded_by_user_id=manager.id,
                    title="Отчет за май",
                    original_filename="may.pdf",
                    stored_filename="may.pdf",
                    stored_path="storage/uploads/may.pdf",
                    size_bytes=100,
                ),
            ]
        )
        db.commit()

        rows = list_admin_report_conversations(db)

    assert len(rows) == 1
    assert rows[0].conversation.title == "Отчеты по рекламе"
    assert rows[0].client is not None and rows[0].client.username == "client"
    assert rows[0].reports[0].title == "Отчет за май"


def test_manager_unread_badge_is_only_actionable_for_current_manager() -> None:
    current_manager_id = 10
    other_manager_id = 20
    message_at = datetime(2026, 5, 16, 12, 0)
    unread_message = Message(sender_type="client", content="Нужен ответ", created_at=message_at)

    unassigned = Appeal(status="new", conversation=Conversation(messages=[unread_message]))
    mine = Appeal(status="assigned_to_manager", assigned_manager_id=current_manager_id, conversation=Conversation(messages=[Message(sender_type="client", content="Мое", created_at=message_at)]))
    other = Appeal(status="assigned_to_manager", assigned_manager_id=other_manager_id, conversation=Conversation(messages=[Message(sender_type="client", content="Чужое", created_at=message_at)]))
    closed = Appeal(status="closed", assigned_manager_id=current_manager_id, conversation=Conversation(messages=[Message(sender_type="client", content="Закрыто", created_at=message_at)]))

    assert actionable_manager_unread_count(unassigned, current_manager_id, "manager") == 1
    assert actionable_manager_unread_count(mine, current_manager_id, "manager") == 1
    assert actionable_manager_unread_count(other, current_manager_id, "manager") == 0
    assert actionable_manager_unread_count(closed, current_manager_id, "manager") == 0


def test_manager_client_helpers_sort_active_first_and_change_type() -> None:
    active = User(username="z-active", email="a@test.local", full_name="Z", role="client", client_type="active_client", hashed_password="x")
    potential = User(username="a-potential", email="p@test.local", full_name="A", role="client", client_type="potential_client", hashed_password="x")
    manager = User(username="manager", email="m@test.local", full_name="M", role="manager", hashed_password="x")

    assert sorted([potential, active], key=client_type_sort_key) == [active, potential]
    assert change_client_type(potential, "active_client") is True
    assert potential.client_type == "active_client"
    assert change_client_type(manager, "active_client") is False


def test_admin_can_archive_clients_and_managers_but_not_admins_or_self() -> None:
    admin = User(id=1, username="admin", email="a@test.local", full_name="Admin", role="admin", hashed_password="x")
    other_admin = User(id=2, username="admin2", email="a2@test.local", full_name="Admin 2", role="admin", hashed_password="x")
    manager = User(id=3, username="manager", email="m@test.local", full_name="Manager", role="manager", hashed_password="x")
    client = User(id=4, username="client", email="c@test.local", full_name="Client", role="client", hashed_password="x")

    assert can_archive_user(client, admin) is True
    assert can_archive_user(manager, admin) is True
    assert can_archive_user(other_admin, admin) is False
    assert can_archive_user(admin, admin) is False


def test_latest_autoanswer_source_summary_uses_latest_response() -> None:
    old = GeneratedResponse(id=1, source="local_rules", response_text="A")
    latest = GeneratedResponse(id=2, source="local_llama_cpp", response_text="B")

    assert latest_generated_response([latest, old]) is latest
    assert source_label(latest.source) == "Локальная языковая модель"
    assert source_label(old.source) == "Автоматический ответ"


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
    assert normalize_ai_feedback("dislike", "other", "Свой вариант") == ("dislike", "other", "Свой вариант")


def test_ai_feedback_custom_reason_required_only_for_other() -> None:
    assert normalize_ai_feedback("dislike", "too_general", "") == ("dislike", "too_general", None)
    try:
        normalize_ai_feedback("dislike", "other", "")
    except ValueError as error:
        assert "причину" in str(error)
    else:
        raise AssertionError("Expected custom reason validation for 'other'.")


def test_admin_manager_rating_rows_include_unrated_managers() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        manager = User(username="manager", email="m@test.local", full_name="Менеджер", role="manager", hashed_password="x")
        db.add(manager)
        db.commit()

        rows = manager_rating_rows(db)

    assert len(rows) == 1
    assert rows[0].manager.username == "manager"
    assert rows[0].summary.average_rating is None
    assert rows[0].summary.rated_count == 0


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
        db.flush()
        category = db.scalar(select(Category).where(Category.slug == "general"))
        db.add_all(
            [
                KnowledgeBaseItem(category_id=category.id, title="Active", content="A", is_active=True),
                KnowledgeBaseItem(category_id=category.id, title="Inactive", content="I", is_active=False),
            ]
        )
        db.commit()

        analytics = build_admin_analytics(db)

    assert percent(1, 4) == 25
    assert grouped_appeal_status("needs_manager") == "manager_needed"
    assert analytics["users"]["total"] == 2
    assert analytics["appeals"]["groups"]["new"] == 1
    assert analytics["appeals"]["groups"]["closed"] == 1
    assert analytics["comments"]["active"] == 1
    assert analytics["comments"]["inactive"] == 1


def test_admin_user_filters_and_category_disable_cascades_comments() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        active_client = User(username="active", email="active@test.local", full_name="Active Client", role="client", client_type="active_client", hashed_password="x", is_active=True)
        archived_manager = User(username="archived", email="arch@test.local", full_name="Archived Manager", role="manager", hashed_password="x", is_active=False)
        category = Category(slug="service-cost", name="service cost", is_active=True)
        db.add_all([active_client, archived_manager, category])
        db.flush()
        comment = KnowledgeBaseItem(category=category, title="Comment", content="Text", is_active=True)
        db.add(comment)
        db.commit()

        filtered = list(db.scalars(apply_user_filters(select(User), role="client", status="active", client_type="active_client", search="active")))
        toggle_category_active(category)
        db.flush()

        assert filtered == [active_client]
        assert category.is_active is False
        assert comment.is_active is False


def test_knowledge_item_search_matches_title_content_category_and_tone() -> None:
    category = Category(slug="service-cost", name="service cost")
    item = KnowledgeBaseItem(category=category, emotional_tone="negative", title="Цена запуска", content="Расскажем про бюджет")
    other = KnowledgeBaseItem(category=Category(slug="other", name="other"), emotional_tone="neutral", title="Другое", content="Нет совпадения")

    assert filter_knowledge_items([item, other], "цена") == [item]
    assert filter_knowledge_items([item, other], "бюджет") == [item]
    assert filter_knowledge_items([item, other], "Стоимость услуг") == [item]
    assert filter_knowledge_items([item, other], "негативный") == [item]


def test_delete_knowledge_item_removes_comment() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        category = Category(slug="other", name="other")
        item = KnowledgeBaseItem(category=category, title="Delete me", content="Text")
        db.add_all([category, item])
        db.commit()

        assert delete_knowledge_item(db, item) is True
        db.commit()

        assert db.scalar(select(func.count(KnowledgeBaseItem.id))) == 0


def test_category_delete_is_blocked_when_comments_exist() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        category = Category(slug="other", name="other")
        db.add(category)
        db.flush()
        db.add(KnowledgeBaseItem(category=category, title="Comment", content="Text"))
        db.commit()
        db.refresh(category)

        error = category_delete_error(db, category)

    assert error == "Нельзя удалить категорию, пока к ней привязаны подготовленные комментарии."
