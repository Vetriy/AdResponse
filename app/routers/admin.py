from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")
router = APIRouter(prefix="/admin", tags=["knowledge base"])


@router.get("/knowledge-base", response_class=HTMLResponse)
async def knowledge_base_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "admin/knowledge_base.html",
        {
            "page_title": "База знаний",
            "active_page": "knowledge",
        },
    )
