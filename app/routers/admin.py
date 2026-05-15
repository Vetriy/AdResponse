from urllib.parse import parse_qs

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

from app.db.session import SessionLocal, database_error_message, get_engine
from app.models import Category, KnowledgeBaseItem

templates = Jinja2Templates(directory="app/templates")
router = APIRouter(prefix="/admin", tags=["knowledge base"])

EMOTIONAL_TONES = ("any", "neutral", "interested", "anxious", "disappointed", "irritated", "negative")


def redirect_to(path: str) -> RedirectResponse:
    return RedirectResponse(path, status_code=303)


def open_db():
    get_engine()
    return SessionLocal()


async def read_form(request: Request) -> dict[str, str]:
    body = (await request.body()).decode()
    return {key: values[-1] for key, values in parse_qs(body, keep_blank_values=True).items()}


def form_bool(form: dict[str, str], key: str) -> bool:
    return form.get(key, "").lower() in {"1", "true", "yes", "on"}


def form_int(form: dict[str, str], key: str, default: int) -> int:
    try:
        return int(form.get(key, str(default)))
    except ValueError:
        return default


def slugify(value: str) -> str:
    return value.strip().lower().replace(" ", "-").replace("_", "-")


@router.get("/knowledge-base", response_class=HTMLResponse)
async def knowledge_base_page(request: Request) -> HTMLResponse:
    try:
        db = open_db()
    except Exception as error:
        return templates.TemplateResponse(
            request,
            "admin/knowledge_base.html",
            {
                "page_title": "База знаний",
                "active_page": "knowledge",
                "categories": [],
                "items": [],
                "db_error": database_error_message(error),
            },
        )

    try:
        categories = list(db.scalars(select(Category).order_by(Category.name.asc())))
        items = list(
            db.scalars(
                select(KnowledgeBaseItem)
                .options(selectinload(KnowledgeBaseItem.category))
                .order_by(KnowledgeBaseItem.priority.asc(), KnowledgeBaseItem.created_at.desc())
            )
        )
        return templates.TemplateResponse(
            request,
            "admin/knowledge_base.html",
            {
                "page_title": "База знаний",
                "active_page": "knowledge",
                "categories": categories,
                "items": items,
                "db_error": None,
            },
        )
    except Exception as error:
        return templates.TemplateResponse(
            request,
            "admin/knowledge_base.html",
            {
                "page_title": "База знаний",
                "active_page": "knowledge",
                "categories": [],
                "items": [],
                "db_error": database_error_message(error),
            },
        )
    finally:
        db.close()


@router.get("/categories/new", response_class=HTMLResponse)
async def new_category(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "admin/category_form.html",
        {
            "page_title": "Новая категория",
            "active_page": "knowledge",
            "category": None,
            "error": "",
            "form_action": "/admin/categories",
        },
    )


@router.post("/categories")
async def create_category(
    request: Request,
):
    form = await read_form(request)
    slug = form.get("slug", "")
    name = form.get("name", "")
    description = form.get("description", "")
    is_active = form_bool(form, "is_active")
    slug = slugify(slug)
    name = name.strip()
    if not slug or not name:
        return templates.TemplateResponse(
            request,
            "admin/category_form.html",
            {
                "page_title": "Новая категория",
                "active_page": "knowledge",
                "category": {"slug": slug, "name": name, "description": description, "is_active": is_active},
                "error": "Заполните slug и название категории.",
                "form_action": "/admin/categories",
            },
        )

    db = open_db()
    try:
        existing = db.scalar(select(Category).where(Category.slug == slug))
        if existing:
            return templates.TemplateResponse(
                request,
                "admin/category_form.html",
                {
                    "page_title": "Новая категория",
                    "active_page": "knowledge",
                    "category": {"slug": slug, "name": name, "description": description, "is_active": is_active},
                    "error": "Категория с таким slug уже существует.",
                    "form_action": "/admin/categories",
                },
            )
        db.add(Category(slug=slug, name=name, description=description.strip() or None, is_active=is_active))
        db.commit()
    finally:
        db.close()
    return redirect_to("/admin/knowledge-base")


@router.get("/categories/{category_id}/edit", response_class=HTMLResponse)
async def edit_category(request: Request, category_id: int) -> HTMLResponse:
    db = open_db()
    try:
        category = db.get(Category, category_id)
        return templates.TemplateResponse(
            request,
            "admin/category_form.html",
            {
                "page_title": "Редактировать категорию",
                "active_page": "knowledge",
                "category": category,
                "error": "" if category else "Категория не найдена.",
                "form_action": f"/admin/categories/{category_id}",
            },
        )
    finally:
        db.close()


@router.post("/categories/{category_id}")
async def update_category(
    request: Request,
    category_id: int,
):
    form = await read_form(request)
    slug = form.get("slug", "")
    name = form.get("name", "")
    description = form.get("description", "")
    is_active = form_bool(form, "is_active")
    slug = slugify(slug)
    name = name.strip()
    db = open_db()
    try:
        category = db.get(Category, category_id)
        if category is None or not slug or not name:
            return templates.TemplateResponse(
                request,
                "admin/category_form.html",
                {
                    "page_title": "Редактировать категорию",
                    "active_page": "knowledge",
                    "category": category,
                    "error": "Проверьте slug и название категории.",
                    "form_action": f"/admin/categories/{category_id}",
                },
            )
        category.slug = slug
        category.name = name
        category.description = description.strip() or None
        category.is_active = is_active
        db.commit()
    finally:
        db.close()
    return redirect_to("/admin/knowledge-base")


@router.post("/categories/{category_id}/delete")
async def delete_category(category_id: int) -> RedirectResponse:
    db = open_db()
    try:
        category = db.get(Category, category_id)
        if category:
            category.is_active = False
            db.commit()
    finally:
        db.close()
    return redirect_to("/admin/knowledge-base")


@router.get("/knowledge-base/items/new", response_class=HTMLResponse)
async def new_knowledge_item(request: Request) -> HTMLResponse:
    db = open_db()
    try:
        categories = list(db.scalars(select(Category).where(Category.is_active.is_(True)).order_by(Category.name.asc())))
        return templates.TemplateResponse(
            request,
            "admin/kb_item_form.html",
            {
                "page_title": "Новый комментарий",
                "active_page": "knowledge",
                "item": None,
                "categories": categories,
                "tones": EMOTIONAL_TONES,
                "error": "",
                "form_action": "/admin/knowledge-base/items",
            },
        )
    finally:
        db.close()


@router.post("/knowledge-base/items")
async def create_knowledge_item(
    request: Request,
):
    form = await read_form(request)
    category_id = form_int(form, "category_id", 0)
    emotional_tone = form.get("emotional_tone", "any")
    title = form.get("title", "")
    content = form.get("content", "")
    priority = form_int(form, "priority", 100)
    is_active = form_bool(form, "is_active")
    db = open_db()
    try:
        categories = list(db.scalars(select(Category).where(Category.is_active.is_(True)).order_by(Category.name.asc())))
        if emotional_tone not in EMOTIONAL_TONES or not title.strip() or not content.strip():
            return templates.TemplateResponse(
                request,
                "admin/kb_item_form.html",
                {
                    "page_title": "Новый комментарий",
                    "active_page": "knowledge",
                    "item": {
                        "category_id": category_id,
                        "emotional_tone": emotional_tone,
                        "title": title,
                        "content": content,
                        "priority": priority,
                        "is_active": is_active,
                    },
                    "categories": categories,
                    "tones": EMOTIONAL_TONES,
                    "error": "Заполните заголовок, текст и корректный эмоциональный тон.",
                    "form_action": "/admin/knowledge-base/items",
                },
            )
        db.add(
            KnowledgeBaseItem(
                category_id=category_id,
                emotional_tone=emotional_tone,
                title=title.strip(),
                content=content.strip(),
                priority=priority,
                is_active=is_active,
            )
        )
        db.commit()
    finally:
        db.close()
    return redirect_to("/admin/knowledge-base")


@router.get("/knowledge-base/items/{item_id}/edit", response_class=HTMLResponse)
async def edit_knowledge_item(request: Request, item_id: int) -> HTMLResponse:
    db = open_db()
    try:
        item = db.get(KnowledgeBaseItem, item_id)
        categories = list(db.scalars(select(Category).where(Category.is_active.is_(True)).order_by(Category.name.asc())))
        return templates.TemplateResponse(
            request,
            "admin/kb_item_form.html",
            {
                "page_title": "Редактировать комментарий",
                "active_page": "knowledge",
                "item": item,
                "categories": categories,
                "tones": EMOTIONAL_TONES,
                "error": "" if item else "Комментарий не найден.",
                "form_action": f"/admin/knowledge-base/items/{item_id}",
            },
        )
    finally:
        db.close()


@router.post("/knowledge-base/items/{item_id}")
async def update_knowledge_item(
    request: Request,
    item_id: int,
):
    form = await read_form(request)
    category_id = form_int(form, "category_id", 0)
    emotional_tone = form.get("emotional_tone", "any")
    title = form.get("title", "")
    content = form.get("content", "")
    priority = form_int(form, "priority", 100)
    is_active = form_bool(form, "is_active")
    db = open_db()
    try:
        item = db.get(KnowledgeBaseItem, item_id)
        categories = list(db.scalars(select(Category).where(Category.is_active.is_(True)).order_by(Category.name.asc())))
        if item is None or emotional_tone not in EMOTIONAL_TONES or not title.strip() or not content.strip():
            return templates.TemplateResponse(
                request,
                "admin/kb_item_form.html",
                {
                    "page_title": "Редактировать комментарий",
                    "active_page": "knowledge",
                    "item": item,
                    "categories": categories,
                    "tones": EMOTIONAL_TONES,
                    "error": "Проверьте категорию, эмоциональный тон, заголовок и текст.",
                    "form_action": f"/admin/knowledge-base/items/{item_id}",
                },
            )
        item.category_id = category_id
        item.emotional_tone = emotional_tone
        item.title = title.strip()
        item.content = content.strip()
        item.priority = priority
        item.is_active = is_active
        db.commit()
    finally:
        db.close()
    return redirect_to("/admin/knowledge-base")


@router.post("/knowledge-base/items/{item_id}/delete")
async def delete_knowledge_item(item_id: int) -> RedirectResponse:
    db = open_db()
    try:
        item = db.get(KnowledgeBaseItem, item_id)
        if item:
            try:
                db.delete(item)
                db.commit()
            except SQLAlchemyError:
                db.rollback()
                item.is_active = False
                db.commit()
    finally:
        db.close()
    return redirect_to("/admin/knowledge-base")
