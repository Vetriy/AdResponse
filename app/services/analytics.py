from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AiResponseFeedback, Appeal, KnowledgeBaseItem, User
from app.services.feedback import DISLIKE_REASONS, dislike_reason_label
from app.services.labels import status_label


APPEAL_STATUS_GROUPS = {
    "new": "Новые",
    "in_progress": "В работе",
    "manager_needed": "Нужен менеджер",
    "closed": "Завершенные",
}


def percent(part: int, total: int) -> int:
    if total <= 0:
        return 0
    return round(part * 100 / total)


def grouped_appeal_status(status: str | None) -> str:
    if status == "new":
        return "new"
    if status == "closed":
        return "closed"
    if status in {"needs_manager", "handover_requested", "needs_clarification"}:
        return "manager_needed"
    return "in_progress"


def build_admin_analytics(db: Session) -> dict:
    role_rows = dict(db.execute(select(User.role, func.count(User.id)).group_by(User.role)).all())
    role_counts = {role: int(role_rows.get(role, 0)) for role in ("client", "manager", "admin")}
    total_users = sum(role_counts.values())

    appeal_rows = dict(db.execute(select(Appeal.status, func.count(Appeal.id)).group_by(Appeal.status)).all())
    appeal_groups = {key: 0 for key in APPEAL_STATUS_GROUPS}
    for status, count in appeal_rows.items():
        appeal_groups[grouped_appeal_status(status)] += int(count)
    total_appeals = sum(appeal_groups.values())

    active_comments = db.scalar(select(func.count(KnowledgeBaseItem.id)).where(KnowledgeBaseItem.is_active.is_(True))) or 0
    total_comments = db.scalar(select(func.count(KnowledgeBaseItem.id))) or 0
    inactive_comments = int(total_comments) - int(active_comments)

    ai_likes = db.scalar(select(func.count(AiResponseFeedback.id)).where(AiResponseFeedback.value == "like")) or 0
    ai_dislikes = db.scalar(select(func.count(AiResponseFeedback.id)).where(AiResponseFeedback.value == "dislike")) or 0
    total_ai_feedback = int(ai_likes) + int(ai_dislikes)
    reason_rows = db.execute(
        select(AiResponseFeedback.reason, func.count(AiResponseFeedback.id))
        .where(AiResponseFeedback.value == "dislike")
        .group_by(AiResponseFeedback.reason)
    )
    dislike_reasons = [
        {"key": reason or "unknown", "label": dislike_reason_label(reason), "count": int(count)}
        for reason, count in reason_rows
    ]
    if not dislike_reasons:
        dislike_reasons = [{"key": key, "label": label, "count": 0} for key, label in DISLIKE_REASONS.items()]

    return {
        "users": {
            "total": total_users,
            "roles": role_counts,
        },
        "appeals": {
            "total": total_appeals,
            "groups": appeal_groups,
            "status_counts": {status: int(count) for status, count in appeal_rows.items()},
        },
        "comments": {
            "total": int(total_comments),
            "active": int(active_comments),
            "inactive": int(inactive_comments),
        },
        "ai_feedback": {
            "likes": int(ai_likes),
            "dislikes": int(ai_dislikes),
            "total": total_ai_feedback,
            "helpfulness_ratio": percent(int(ai_likes), total_ai_feedback),
            "reasons": dislike_reasons,
        },
    }


def status_rows_for_chart(status_counts: dict[str, int]) -> list[dict[str, int | str]]:
    return [
        {"status": status, "label": status_label(status), "count": count}
        for status, count in sorted(status_counts.items(), key=lambda item: item[0])
    ]
