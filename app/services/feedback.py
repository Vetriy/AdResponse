from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AiResponseFeedback, AppealFeedback, User


DISLIKE_REASONS = {
    "off_topic": "Не по теме",
    "too_general": "Слишком общий ответ",
    "not_helpful": "Не помог решить вопрос",
    "wrong_info": "Ошибочная информация",
    "bad_tone": "Неподходящий тон",
    "other": "Другое",
}


@dataclass(frozen=True)
class ManagerRatingSummary:
    average_rating: float | None
    rated_count: int


@dataclass(frozen=True)
class ManagerRatingRow:
    manager: User
    summary: ManagerRatingSummary


def dislike_reason_label(value: str | None) -> str:
    return DISLIKE_REASONS.get(value or "", value or "Причина не указана")


def normalize_ai_feedback(value: str, reason: str | None = None, custom_reason: str | None = None) -> tuple[str, str | None, str | None]:
    normalized_value = value.strip().lower()
    if normalized_value not in {"like", "dislike"}:
        raise ValueError("Некорректная оценка ответа.")

    normalized_reason = (reason or "").strip()
    normalized_custom = (custom_reason or "").strip()
    if normalized_value == "like":
        return normalized_value, None, None

    if normalized_reason not in DISLIKE_REASONS:
        raise ValueError("Выберите причину отрицательной оценки.")
    if normalized_reason == "other" and not normalized_custom:
        raise ValueError("Коротко укажите причину.")
    return normalized_value, normalized_reason, normalized_custom[:300] or None


def manager_rating_summary(db: Session, manager_id: int | None = None) -> ManagerRatingSummary:
    statement = select(func.avg(AppealFeedback.rating), func.count(AppealFeedback.id))
    if manager_id is not None:
        statement = statement.where(AppealFeedback.manager_user_id == manager_id)
    average, count = db.execute(statement).one()
    return ManagerRatingSummary(round(float(average), 2) if average is not None else None, int(count or 0))


def manager_rating_rows(db: Session) -> list[ManagerRatingRow]:
    managers = list(db.scalars(select(User).where(User.role == "manager").order_by(User.full_name.asc(), User.username.asc())))
    return [ManagerRatingRow(manager=manager, summary=manager_rating_summary(db, manager.id)) for manager in managers]


def store_or_update_ai_feedback(
    db: Session,
    *,
    message_id: int,
    appeal_id: int,
    client_user_id: int,
    value: str,
    reason: str | None = None,
    custom_reason: str | None = None,
) -> AiResponseFeedback:
    normalized_value, normalized_reason, normalized_custom = normalize_ai_feedback(value, reason, custom_reason)
    feedback = db.scalar(
        select(AiResponseFeedback).where(
            AiResponseFeedback.message_id == message_id,
            AiResponseFeedback.client_user_id == client_user_id,
        )
    )
    if feedback is None:
        feedback = AiResponseFeedback(
            message_id=message_id,
            appeal_id=appeal_id,
            client_user_id=client_user_id,
            value=normalized_value,
            reason=normalized_reason,
            custom_reason=normalized_custom,
        )
        db.add(feedback)
    else:
        feedback.value = normalized_value
        feedback.reason = normalized_reason
        feedback.custom_reason = normalized_custom
    return feedback


def client_ai_feedback_map(db: Session, client_user_id: int, message_ids: list[int]) -> dict[int, AiResponseFeedback]:
    if not message_ids:
        return {}
    rows = db.scalars(
        select(AiResponseFeedback).where(
            AiResponseFeedback.client_user_id == client_user_id,
            AiResponseFeedback.message_id.in_(message_ids),
        )
    )
    return {feedback.message_id: feedback for feedback in rows}


def client_feedback_for_appeal(db: Session, appeal_id: int, client_user_id: int) -> AppealFeedback | None:
    return db.scalar(
        select(AppealFeedback).where(
            AppealFeedback.appeal_id == appeal_id,
            AppealFeedback.client_user_id == client_user_id,
        )
    )


def role_counts(db: Session) -> dict[str, int]:
    rows = db.execute(select(User.role, func.count(User.id)).group_by(User.role))
    return {role: int(count) for role, count in rows}
