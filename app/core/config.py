import os
from dataclasses import dataclass
from urllib.parse import quote_plus


try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency is installed in normal setup.
    load_dotenv = None


if load_dotenv:
    load_dotenv()


def build_database_url() -> str:
    explicit_url = os.getenv("DATABASE_URL")
    if explicit_url:
        return explicit_url

    user = quote_plus(os.getenv("DATABASE_USER", "adresponse"))
    password = quote_plus(os.getenv("DATABASE_PASSWORD", "adresponse"))
    host = os.getenv("DATABASE_HOST", "localhost")
    port = os.getenv("DATABASE_PORT", "5432")
    name = os.getenv("DATABASE_NAME", "adresponse")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{name}"


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "AdResponse")
    debug: bool = os.getenv("DEBUG", "true").lower() in {"1", "true", "yes", "on"}
    database_host: str = os.getenv("DATABASE_HOST", "localhost")
    database_port: str = os.getenv("DATABASE_PORT", "5432")
    database_name: str = os.getenv("DATABASE_NAME", "adresponse")
    database_user: str = os.getenv("DATABASE_USER", "adresponse")
    database_password: str = os.getenv("DATABASE_PASSWORD", "adresponse")
    database_url: str = build_database_url()


settings = Settings()
