from fastapi import Request
from fastapi.templating import Jinja2Templates

from app.services.labels import (
    appeal_category_label,
    category_label,
    client_identifier,
    client_type_label,
    latest_generated_response,
    message_author_name,
    message_date_label,
    message_role_label,
    sender_label,
    role_label,
    source_label,
    status_label,
    tone_label,
)
from app.services.feedback import DISLIKE_REASONS, dislike_reason_label
from app.services.manager_workflow import (
    actionable_manager_unread_count,
    assignment_badge_label,
    assignment_group,
    latest_client_activity,
    unread_messages_count,
)
from app.services.analytics import percent


def inject_current_user(request: Request) -> dict:
    return {"current_user": request.session.get("user")}


def create_templates() -> Jinja2Templates:
    templates = Jinja2Templates(directory="app/templates", context_processors=[inject_current_user])
    templates.env.globals.update(
        appeal_category_label=appeal_category_label,
        category_label=category_label,
        client_identifier=client_identifier,
        client_type_label=client_type_label,
        latest_generated_response=latest_generated_response,
        message_author_name=message_author_name,
        message_date_label=message_date_label,
        message_role_label=message_role_label,
        sender_label=sender_label,
        role_label=role_label,
        source_label=source_label,
        status_label=status_label,
        tone_label=tone_label,
        assignment_badge_label=assignment_badge_label,
        assignment_group=assignment_group,
        actionable_manager_unread_count=actionable_manager_unread_count,
        dislike_reason_label=dislike_reason_label,
        dislike_reasons=DISLIKE_REASONS,
        latest_client_activity=latest_client_activity,
        unread_messages_count=unread_messages_count,
        percent=percent,
    )
    return templates
