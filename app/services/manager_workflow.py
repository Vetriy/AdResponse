from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import AdvertisingReport, Appeal, ClientSession, Conversation, Message, User


@dataclass(frozen=True)
class ManagerClientRow:
    client: User
    total_appeals: int
    active_appeals: int
    last_appeal_at: datetime | None
    last_report_at: datetime | None
    report_conversation_id: int | None
    unread_report_messages: int


def resolve_appeal_client(appeal: Appeal | None) -> User | None:
    if appeal is None or appeal.conversation is None or appeal.conversation.client_session is None:
        return None
    session = appeal.conversation.client_session
    return session.user


def resolve_appeal_client_user(db: Session, appeal: Appeal | None) -> User | None:
    client = resolve_appeal_client(appeal)
    if client is not None:
        return client
    if appeal is None or appeal.conversation is None or appeal.conversation.client_session is None:
        return None
    contact = (appeal.conversation.client_session.client_contact or "").strip().lower()
    if not contact:
        return None
    return db.scalar(select(User).where(User.email == contact, User.role == "client"))


def assignment_group(appeal: Appeal, current_manager_id: int | None) -> str:
    if appeal.status == "closed":
        return "completed"
    if appeal.assigned_manager_id is None:
        return "unassigned"
    if current_manager_id is not None and appeal.assigned_manager_id == current_manager_id:
        return "mine"
    return "other"


def assignment_badge_label(group: str) -> str:
    return {
        "unassigned": "Без менеджера",
        "mine": "Закреплено за мной",
        "other": "Закреплено за другим менеджером",
        "completed": "Завершено",
    }.get(group, "Обращение")


def finish_appeal_for_manager(appeal: Appeal | None, manager: User) -> bool:
    if appeal is None:
        return False
    if manager.role != "admin" and appeal.assigned_manager_id not in {None, manager.id}:
        return False
    if appeal.assigned_manager_id is None:
        appeal.assigned_manager_id = manager.id
    appeal.status = "closed"
    return True


def client_type_sort_key(client: User) -> tuple[int, str, str]:
    type_rank = 0 if client.client_type == "active_client" else 1
    return (type_rank, (client.full_name or "").lower(), client.username.lower())


def change_client_type(client: User | None, client_type: str) -> bool:
    if client is None or client.role != "client":
        return False
    if client_type not in {"active_client", "potential_client"}:
        return False
    client.client_type = client_type
    return True


def latest_client_activity(appeal: Appeal) -> datetime:
    client_messages = [message.created_at for message in appeal.conversation.messages if message.sender_type == "client" and message.created_at]
    if client_messages:
        return max(client_messages)
    return appeal.created_at or datetime.min


def mark_conversation_read(conversation: Conversation | None, role: str) -> None:
    if conversation is None:
        return
    now = datetime.now(UTC)
    if role == "client":
        conversation.client_last_read_at = now
    elif role in {"manager", "admin"}:
        conversation.manager_last_read_at = now


def is_after_read_marker(message_at: datetime | None, read_at: datetime | None) -> bool:
    if message_at is None:
        return False
    if read_at is None:
        return True
    if (message_at.tzinfo is None) != (read_at.tzinfo is None):
        message_at = message_at.replace(tzinfo=None)
        read_at = read_at.replace(tzinfo=None)
    return message_at > read_at


def unread_messages_count(conversation: Conversation | None, role: str) -> int:
    if conversation is None:
        return 0
    if role == "client":
        read_at = conversation.client_last_read_at
        sender_types = {"manager", "system"}
    else:
        read_at = conversation.manager_last_read_at
        sender_types = {"client"}
    return sum(
        1
        for message in conversation.messages
        if message.sender_type in sender_types and is_after_read_marker(message.created_at, read_at)
    )


def group_manager_appeals(appeals: list[Appeal], current_manager_id: int | None) -> dict[str, list[Appeal]]:
    sorted_appeals = sorted(appeals, key=latest_client_activity, reverse=True)
    groups = {"unassigned": [], "mine": [], "other": [], "completed": []}
    for appeal in sorted_appeals:
        groups[assignment_group(appeal, current_manager_id)].append(appeal)
    return groups


def list_manager_clients(db: Session) -> list[ManagerClientRow]:
    clients = sorted(
        db.scalars(select(User).where(User.role == "client")).all(),
        key=client_type_sort_key,
    )
    rows: list[ManagerClientRow] = []
    for client in clients:
        appeal_base = (
            select(Appeal)
            .join(Appeal.conversation)
            .join(Conversation.client_session)
            .where(ClientSession.user_id == client.id)
        )
        total = db.scalar(select(func.count()).select_from(appeal_base.subquery())) or 0
        active = db.scalar(select(func.count()).select_from(appeal_base.where(Appeal.status != "closed").subquery())) or 0
        last_appeal_at = db.scalar(
            select(func.max(Message.created_at))
            .join(Message.conversation)
            .join(Conversation.client_session)
            .where(ClientSession.user_id == client.id, Message.sender_type == "client")
        )
        last_report_at = db.scalar(select(func.max(AdvertisingReport.created_at)).where(AdvertisingReport.client_user_id == client.id))
        report_conversation = get_report_conversation(db, client.id)
        rows.append(
            ManagerClientRow(
                client=client,
                total_appeals=int(total),
                active_appeals=int(active),
                last_appeal_at=last_appeal_at,
                last_report_at=last_report_at,
                report_conversation_id=report_conversation.id if report_conversation else None,
                unread_report_messages=unread_messages_count(report_conversation, "manager"),
            )
        )
    return rows


def get_report_conversation(db: Session, client_user_id: int) -> Conversation | None:
    return db.scalar(
        select(Conversation)
        .join(Conversation.client_session)
        .where(
            ClientSession.user_id == client_user_id,
            Conversation.conversation_type == "report_thread",
        )
        .options(
            selectinload(Conversation.messages),
            selectinload(Conversation.messages).selectinload(Message.attachments),
            selectinload(Conversation.advertising_reports),
            selectinload(Conversation.client_session).selectinload(ClientSession.user),
        )
        .order_by(Conversation.created_at.asc())
    )


def get_or_create_report_conversation(db: Session, client: User) -> Conversation:
    conversation = get_report_conversation(db, client.id)
    if conversation is not None:
        return conversation

    client_session = ClientSession(
        user_id=client.id,
        client_name=client.full_name,
        client_contact=client.email,
        source="report_thread",
        status="active",
    )
    conversation = Conversation(
        client_session=client_session,
        title="Отчеты по рекламе",
        status="open",
        conversation_type="report_thread",
    )
    db.add(conversation)
    db.flush()
    return conversation
