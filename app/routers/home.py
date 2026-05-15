from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.core.templates import create_templates

templates = create_templates()
router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def home_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "home.html",
        {
            "page_title": "Главная",
            "active_page": "home",
        },
    )
