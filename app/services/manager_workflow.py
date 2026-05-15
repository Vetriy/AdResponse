from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AdvertisingReport, Appeal, ClientSession, Conversation, Message, User


@dataclass(frozen=True)
class ManagerClientRow:
    client: User
    total_appeals: int
    active_appeals: int
    last_appeal_at: datetime | None
    last_report_at: datetime | None


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


def latest_client_activity(appeal: Appeal) -> datetime:
    client_messages = [message.created_at for message in appeal.conversation.messages if message.sender_type == "client" and message.created_at]
    if client_messages:
        return max(client_messages)
    return appeal.created_at or datetime.min


def group_manager_appeals(appeals: list[Appeal], current_manager_id: int | None) -> dict[str, list[Appeal]]:
    sorted_appeals = sorted(appeals, key=latest_client_activity, reverse=True)
    groups = {"unassigned": [], "mine": [], "other": [], "completed": []}
    for appeal in sorted_appeals:
        groups[assignment_group(appeal, current_manager_id)].append(appeal)
    return groups


def list_manager_clients(db: Session) -> list[ManagerClientRow]:
    clients = list(db.scalars(select(User).where(User.role == "client").order_by(User.full_name.asc(), User.username.asc())))
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
        rows.append(
            ManagerClientRow(
                client=client,
                total_appeals=int(total),
                active_appeals=int(active),
                last_appeal_at=last_appeal_at,
                last_report_at=last_report_at,
            )
        )
    return rows
