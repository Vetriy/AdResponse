from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")
router = APIRouter(prefix="/manager", tags=["manager dashboard"])


@router.get("/", response_class=HTMLResponse)
async def manager_dashboard(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "manager/dashboard.html",
        {
            "page_title": "Панель менеджера",
            "active_page": "manager",
        },
    )
