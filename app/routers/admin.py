from urllib.parse import parse_qs

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.core.auth import login_redirect, require_role
from app.core.security import hash_password
from app.core.templates import create_templates
from app.db.session import SessionLocal, database_error_message, get_engine
from app.models import AdvertisingReport, Appeal, Category, KnowledgeBaseItem, User
from app.services.analytics import build_admin_analytics, status_rows_for_chart
from app.services.feedback import manager_rating_rows

templates = create_templates()
router = APIRouter(prefix="/admin", tags=["knowledge base"])

EMOTIONAL_TONES = ("any", "neutral", "interested", "anxious", "disappointed", "irritated", "negative")
USER_ROLES = ("client", "manager", "admin")
CLIENT_TYPES = ("active_client", "potential_client")


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


def ensure_admin(request: Request, db):
    return require_role(request, db, {"admin"})


def can_archive_user(target: User | None, current_admin: User) -> bool:
    return target is not None and target.role in {"client", "manager"} and target.id != current_admin.id


def toggle_category_active(category: Category | None) -> bool:
    if category is None:
        return False
    disabling = category.is_active
    category.is_active = not category.is_active
    if disabling:
        for item in category.knowledge_base_items:
            item.is_active = False
    return True


def apply_user_filters(statement, role: str = "", status: str = "", client_type: str = "", search: str = ""):
    if role in USER_ROLES:
        statement = statement.where(User.role == role)
    if status == "active":
        statement = statement.where(User.is_active.is_(True))
    elif status == "inactive":
        statement = statement.where(User.is_active.is_(False))
    if client_type in CLIENT_TYPES:
        statement = statement.where(User.role == "client", User.client_type == client_type)
    if search.strip():
        pattern = f"%{search.strip().lower()}%"
        statement = statement.where(
            func.lower(User.username).like(pattern)
            | func.lower(User.email).like(pattern)
            | func.lower(User.full_name).like(pattern)
        )
    return statement


@router.get("/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request) -> HTMLResponse:
    if not request.session.get("user"):
        return login_redirect(request)
    db = open_db()
    try:
        user = ensure_admin(request, db)
        if not hasattr(user, "id"):
            return user
        stats = {
            "users": db.scalar(select(func.count(User.id))) or 0,
            "clients": db.scalar(select(func.count(User.id)).where(User.role == "client")) or 0,
            "managers": db.scalar(select(func.count(User.id)).where(User.role == "manager")) or 0,
            "admins": db.scalar(select(func.count(User.id)).where(User.role == "admin")) or 0,
            "active_clients": db.scalar(select(func.count(User.id)).where(User.role == "client", User.client_type == "active_client")) or 0,
            "potential_clients": db.scalar(select(func.count(User.id)).where(User.role == "client", User.client_type == "potential_client")) or 0,
            "appeals": db.scalar(select(func.count(Appeal.id))) or 0,
            "new_appeals": db.scalar(select(func.count(Appeal.id)).where(Appeal.status == "new")) or 0,
            "manager_attention": db.scalar(
                select(func.count(Appeal.id)).where(Appeal.status.in_(("needs_manager", "handover_requested", "needs_clarification")))
            )
            or 0,
            "closed_appeals": db.scalar(select(func.count(Appeal.id)).where(Appeal.status == "closed")) or 0,
            "comments": db.scalar(select(func.count(KnowledgeBaseItem.id))) or 0,
            "active_comments": db.scalar(select(func.count(KnowledgeBaseItem.id)).where(KnowledgeBaseItem.is_active.is_(True))) or 0,
            "inactive_comments": db.scalar(select(func.count(KnowledgeBaseItem.id)).where(KnowledgeBaseItem.is_active.is_(False))) or 0,
            "reports": db.scalar(select(func.count(AdvertisingReport.id))) or 0,
        }
        analytics = build_admin_analytics(db)
        return templates.TemplateResponse(
            request,
            "admin/dashboard.html",
            {
                "page_title": "Админ-панель",
                "active_page": "admin",
                "stats": stats,
                "analytics": analytics,
                "manager_ratings": manager_rating_rows(db),
                "status_chart_rows": status_rows_for_chart(analytics["appeals"]["status_counts"]),
            },
        )
    finally:
        db.close()


@router.get("/knowledge-base", response_class=HTMLResponse)
async def knowledge_base_page(request: Request) -> HTMLResponse:
    if not request.session.get("user"):
        return login_redirect(request)
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
        admin = ensure_admin(request, db)
        if not hasattr(admin, "id"):
            return admin
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
    if not request.session.get("user"):
        return login_redirect(request)
    db = open_db()
    try:
        admin = ensure_admin(request, db)
        if not hasattr(admin, "id"):
            return admin
    finally:
        db.close()
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
    if not request.session.get("user"):
        return login_redirect(request)
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
        admin = ensure_admin(request, db)
        if not hasattr(admin, "id"):
            return admin
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
    return redirect_to("/admin/knowledge-base#categories")


@router.get("/categories/{category_id}/edit", response_class=HTMLResponse)
async def edit_category(request: Request, category_id: int) -> HTMLResponse:
    if not request.session.get("user"):
        return login_redirect(request)
    db = open_db()
    try:
        admin = ensure_admin(request, db)
        if not hasattr(admin, "id"):
            return admin
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
    if not request.session.get("user"):
        return login_redirect(request)
    form = await read_form(request)
    slug = form.get("slug", "")
    name = form.get("name", "")
    description = form.get("description", "")
    is_active = form_bool(form, "is_active")
    slug = slugify(slug)
    name = name.strip()
    db = open_db()
    try:
        admin = ensure_admin(request, db)
        if not hasattr(admin, "id"):
            return admin
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
    return redirect_to("/admin/knowledge-base#categories")


@router.post("/categories/{category_id}/delete")
async def delete_category(request: Request, category_id: int) -> RedirectResponse:
    if not request.session.get("user"):
        return login_redirect(request)
    db = open_db()
    try:
        admin = ensure_admin(request, db)
        if not hasattr(admin, "id"):
            return admin
        category = db.get(Category, category_id)
        if category:
            toggle_category_active(category)
            db.commit()
    finally:
        db.close()
    return redirect_to("/admin/knowledge-base#categories")


@router.get("/knowledge-base/items/new", response_class=HTMLResponse)
async def new_knowledge_item(request: Request) -> HTMLResponse:
    if not request.session.get("user"):
        return login_redirect(request)
    db = open_db()
    try:
        admin = ensure_admin(request, db)
        if not hasattr(admin, "id"):
            return admin
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
    if not request.session.get("user"):
        return login_redirect(request)
    form = await read_form(request)
    category_id = form_int(form, "category_id", 0)
    emotional_tone = form.get("emotional_tone", "any")
    title = form.get("title", "")
    content = form.get("content", "")
    priority = form_int(form, "priority", 100)
    is_active = form_bool(form, "is_active")
    db = open_db()
    try:
        admin = ensure_admin(request, db)
        if not hasattr(admin, "id"):
            return admin
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
    return redirect_to("/admin/knowledge-base#comments")


@router.get("/knowledge-base/items/{item_id}/edit", response_class=HTMLResponse)
async def edit_knowledge_item(request: Request, item_id: int) -> HTMLResponse:
    if not request.session.get("user"):
        return login_redirect(request)
    db = open_db()
    try:
        admin = ensure_admin(request, db)
        if not hasattr(admin, "id"):
            return admin
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
    if not request.session.get("user"):
        return login_redirect(request)
    form = await read_form(request)
    category_id = form_int(form, "category_id", 0)
    emotional_tone = form.get("emotional_tone", "any")
    title = form.get("title", "")
    content = form.get("content", "")
    priority = form_int(form, "priority", 100)
    is_active = form_bool(form, "is_active")
    db = open_db()
    try:
        admin = ensure_admin(request, db)
        if not hasattr(admin, "id"):
            return admin
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
    return redirect_to("/admin/knowledge-base#comments")


@router.post("/knowledge-base/items/{item_id}/delete")
async def delete_knowledge_item(request: Request, item_id: int) -> RedirectResponse:
    if not request.session.get("user"):
        return login_redirect(request)
    db = open_db()
    try:
        admin = ensure_admin(request, db)
        if not hasattr(admin, "id"):
            return admin
        item = db.get(KnowledgeBaseItem, item_id)
        if item:
            item.is_active = not item.is_active
            db.commit()
    finally:
        db.close()
    return redirect_to("/admin/knowledge-base#comments")


@router.get("/users", response_class=HTMLResponse)
async def users_page(
    request: Request,
    role: str = "",
    status: str = "",
    client_type: str = "",
    search: str = "",
) -> HTMLResponse:
    if not request.session.get("user"):
        return login_redirect(request)
    db = open_db()
    try:
        admin = ensure_admin(request, db)
        if not hasattr(admin, "id"):
            return admin
        statement = apply_user_filters(select(User), role=role, status=status, client_type=client_type, search=search)
        users = list(db.scalars(statement.order_by(User.role.asc(), User.username.asc())))
        return templates.TemplateResponse(
            request,
            "admin/users.html",
            {
                "page_title": "Пользователи",
                "active_page": "users",
                "users": users,
                "roles": USER_ROLES,
                "client_types": CLIENT_TYPES,
                "filters": {"role": role, "status": status, "client_type": client_type, "search": search},
            },
        )
    finally:
        db.close()


@router.get("/users/create", response_class=HTMLResponse)
async def create_user_page(request: Request) -> HTMLResponse:
    if not request.session.get("user"):
        return login_redirect(request)
    db = open_db()
    try:
        admin = ensure_admin(request, db)
        if not hasattr(admin, "id"):
            return admin
    finally:
        db.close()
    return templates.TemplateResponse(
        request,
        "admin/user_form.html",
        {
            "page_title": "Новый пользователь",
            "active_page": "users",
            "user": None,
            "roles": USER_ROLES,
            "client_types": CLIENT_TYPES,
            "error": "",
            "form_action": "/admin/users/create",
        },
    )


@router.post("/users/create")
async def create_user(request: Request):
    if not request.session.get("user"):
        return login_redirect(request)
    form = await read_form(request)
    username = form.get("username", "").strip().lower()
    email = form.get("email", "").strip().lower()
    full_name = form.get("full_name", "").strip()
    role = form.get("role", "client")
    client_type = form.get("client_type", "potential_client")
    password = form.get("password", "")
    is_active = form_bool(form, "is_active")
    error = ""
    if not username or not email or not full_name or not password or role not in USER_ROLES or client_type not in CLIENT_TYPES:
        error = "Заполните все поля и выберите корректную роль."
    elif len(password) < 6:
        error = "Пароль должен содержать минимум 6 символов."

    db = open_db()
    try:
        admin = ensure_admin(request, db)
        if not hasattr(admin, "id"):
            return admin
        if not error and db.scalar(select(User).where((User.username == username) | (User.email == email))):
            error = "Пользователь с таким логином или email уже существует."
        if error:
            return templates.TemplateResponse(
                request,
                "admin/user_form.html",
                {
                    "page_title": "Новый пользователь",
                    "active_page": "users",
                    "user": {
                        "username": username,
                        "email": email,
                        "full_name": full_name,
                        "role": role,
                        "client_type": client_type,
                        "is_active": is_active,
                    },
                    "roles": USER_ROLES,
                    "client_types": CLIENT_TYPES,
                    "error": error,
                    "form_action": "/admin/users/create",
                },
            )
        db.add(
            User(
                username=username,
                email=email,
                full_name=full_name,
                role=role,
                client_type=client_type if role == "client" else "potential_client",
                hashed_password=hash_password(password),
                is_active=is_active,
            )
        )
        db.commit()
        return redirect_to("/admin/users")
    finally:
        db.close()


@router.get("/users/{user_id}/edit", response_class=HTMLResponse)
async def edit_user_page(request: Request, user_id: int) -> HTMLResponse:
    if not request.session.get("user"):
        return login_redirect(request)
    db = open_db()
    try:
        admin = ensure_admin(request, db)
        if not hasattr(admin, "id"):
            return admin
        user = db.get(User, user_id)
        return templates.TemplateResponse(
            request,
            "admin/user_form.html",
            {
                "page_title": "Редактировать пользователя",
                "active_page": "users",
                "user": user,
                "roles": USER_ROLES,
                "client_types": CLIENT_TYPES,
                "error": "" if user else "Пользователь не найден.",
                "form_action": f"/admin/users/{user_id}/edit",
            },
        )
    finally:
        db.close()


@router.post("/users/{user_id}/edit")
async def edit_user(request: Request, user_id: int):
    if not request.session.get("user"):
        return login_redirect(request)
    form = await read_form(request)
    db = open_db()
    try:
        admin = ensure_admin(request, db)
        if not hasattr(admin, "id"):
            return admin
        user = db.get(User, user_id)
        username = form.get("username", "").strip().lower()
        email = form.get("email", "").strip().lower()
        full_name = form.get("full_name", "").strip()
        role = form.get("role", "client")
        client_type = form.get("client_type", "potential_client")
        is_active = form_bool(form, "is_active")
        if user is None or not username or not email or not full_name or role not in USER_ROLES or client_type not in CLIENT_TYPES:
            return templates.TemplateResponse(
                request,
                "admin/user_form.html",
                {
                    "page_title": "Редактировать пользователя",
                    "active_page": "users",
                    "user": user,
                    "roles": USER_ROLES,
                    "client_types": CLIENT_TYPES,
                    "error": "Проверьте поля пользователя.",
                    "form_action": f"/admin/users/{user_id}/edit",
                },
            )
        duplicate = db.scalar(select(User).where(((User.username == username) | (User.email == email)), User.id != user_id))
        if duplicate:
            return templates.TemplateResponse(
                request,
                "admin/user_form.html",
                {
                    "page_title": "Редактировать пользователя",
                    "active_page": "users",
                    "user": user,
                    "roles": USER_ROLES,
                    "client_types": CLIENT_TYPES,
                    "error": "Логин или email уже занят.",
                    "form_action": f"/admin/users/{user_id}/edit",
                },
            )
        user.username = username
        user.email = email
        user.full_name = full_name
        user.role = role
        user.client_type = client_type if role == "client" else "potential_client"
        user.is_active = is_active
        db.commit()
        return redirect_to("/admin/users")
    finally:
        db.close()


@router.get("/users/{user_id}/reset-password", response_class=HTMLResponse)
async def reset_password_page(request: Request, user_id: int) -> HTMLResponse:
    if not request.session.get("user"):
        return login_redirect(request)
    db = open_db()
    try:
        admin = ensure_admin(request, db)
        if not hasattr(admin, "id"):
            return admin
        user = db.get(User, user_id)
        return templates.TemplateResponse(
            request,
            "admin/reset_password.html",
            {"page_title": "Сброс пароля", "active_page": "users", "user": user, "error": ""},
        )
    finally:
        db.close()


@router.post("/users/{user_id}/reset-password")
async def reset_password(request: Request, user_id: int):
    if not request.session.get("user"):
        return login_redirect(request)
    form = await read_form(request)
    password = form.get("password", "")
    db = open_db()
    try:
        admin = ensure_admin(request, db)
        if not hasattr(admin, "id"):
            return admin
        user = db.get(User, user_id)
        if user is None or len(password) < 6:
            return templates.TemplateResponse(
                request,
                "admin/reset_password.html",
                {"page_title": "Сброс пароля", "active_page": "users", "user": user, "error": "Пароль должен содержать минимум 6 символов."},
            )
        user.hashed_password = hash_password(password)
        db.commit()
        return redirect_to("/admin/users")
    finally:
        db.close()


@router.post("/users/{user_id}/toggle-active")
async def toggle_user_active(request: Request, user_id: int):
    if not request.session.get("user"):
        return login_redirect(request)
    db = open_db()
    try:
        admin = ensure_admin(request, db)
        if not hasattr(admin, "id"):
            return admin
        user = db.get(User, user_id)
        if can_archive_user(user, admin):
            user.is_active = not user.is_active
            db.commit()
    finally:
        db.close()
    return redirect_to("/admin/users")


@router.post("/users/{user_id}/delete")
async def delete_user(request: Request, user_id: int):
    if not request.session.get("user"):
        return login_redirect(request)
    db = open_db()
    try:
        admin = ensure_admin(request, db)
        if not hasattr(admin, "id"):
            return admin
        user = db.get(User, user_id)
        if can_archive_user(user, admin):
            user.is_active = False
            db.commit()
    finally:
        db.close()
    return redirect_to("/admin/users")
