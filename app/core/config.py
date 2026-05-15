import os
from dataclasses import dataclass


try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency is installed in normal setup.
    load_dotenv = None


if load_dotenv:
    load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "AdResponse")
    debug: bool = os.getenv("DEBUG", "true").lower() in {"1", "true", "yes", "on"}


settings = Settings()
