import os
from dataclasses import dataclass
from urllib.parse import quote_plus


try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency is installed in normal setup.
    load_dotenv = None


if load_dotenv:
    load_dotenv()


def read_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


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
    debug: bool = read_bool("DEBUG", True)
    secret_key: str = os.getenv("SECRET_KEY", "change-me-for-local-development")
    database_host: str = os.getenv("DATABASE_HOST", "localhost")
    database_port: str = os.getenv("DATABASE_PORT", "5432")
    database_name: str = os.getenv("DATABASE_NAME", "adresponse")
    database_user: str = os.getenv("DATABASE_USER", "adresponse")
    database_password: str = os.getenv("DATABASE_PASSWORD", "adresponse")
    database_url: str = build_database_url()
    use_llama: bool = read_bool("USE_LLAMA", False)
    llama_base_url: str = os.getenv("LLAMA_BASE_URL", "http://localhost:8080/v1/chat/completions")
    llama_model_name: str = os.getenv("LLAMA_MODEL_NAME", "local-model")
    llama_timeout_seconds: float = float(os.getenv("LLAMA_TIMEOUT_SECONDS", "20"))


settings = Settings()
