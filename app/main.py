from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.routers import admin, chat, home, manager


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description="Interactive service for primary response to advertising agency client requests.",
        version="0.1.0",
    )

    app.mount("/static", StaticFiles(directory="app/static"), name="static")

    app.include_router(home.router)
    app.include_router(chat.router)
    app.include_router(manager.router)
    app.include_router(admin.router)

    return app


app = create_app()
