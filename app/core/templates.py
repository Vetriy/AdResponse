from fastapi import Request
from fastapi.templating import Jinja2Templates


def inject_current_user(request: Request) -> dict:
    return {"current_user": request.session.get("user")}


def create_templates() -> Jinja2Templates:
    return Jinja2Templates(directory="app/templates", context_processors=[inject_current_user])
