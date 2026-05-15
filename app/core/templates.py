from fastapi import Request
from fastapi.templating import Jinja2Templates

from app.services.labels import (
    appeal_category_label,
    category_label,
    client_identifier,
    sender_label,
    role_label,
    source_label,
    status_label,
    tone_label,
)


def inject_current_user(request: Request) -> dict:
    return {"current_user": request.session.get("user")}


def create_templates() -> Jinja2Templates:
    templates = Jinja2Templates(directory="app/templates", context_processors=[inject_current_user])
    templates.env.globals.update(
        appeal_category_label=appeal_category_label,
        category_label=category_label,
        client_identifier=client_identifier,
        sender_label=sender_label,
        role_label=role_label,
        source_label=source_label,
        status_label=status_label,
        tone_label=tone_label,
    )
    return templates
