import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel


BACKEND_DIR = Path(__file__).resolve().parents[2]
WORKSPACE_DIR = BACKEND_DIR.parent

# Load workspace-level and backend-level env files.
for env_file in (
    WORKSPACE_DIR / ".env",
    WORKSPACE_DIR / ".env.local",
    BACKEND_DIR / ".env",
    BACKEND_DIR / ".env.local",
):
    if env_file.exists():
        load_dotenv(env_file, override=False)


def _as_bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _as_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _as_str_list(name: str, default: list[str]) -> list[str]:
    raw = os.getenv(name)
    if raw is None:
        return default
    values = [item.strip() for item in raw.split(",") if item.strip()]
    return values or default


class Settings(BaseModel):
    app_name: str = "HyperAgents API"
    app_version: str = "0.1.0"
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@localhost:5432/hyperagents",
    )
    auto_create_tables: bool = _as_bool("AUTO_CREATE_TABLES", False)
    cors_allow_origins: list[str] = _as_str_list(
        "CORS_ALLOW_ORIGINS",
        ["http://localhost:5173", "http://127.0.0.1:5173"],
    )
    memory_embedding_dimensions: int = _as_int("MEMORY_EMBEDDING_DIMENSIONS", 1536)
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_base_url: str | None = os.getenv("OPENAI_BASE_URL")
    openai_default_model: str = os.getenv("OPENAI_DEFAULT_MODEL", "gpt-4o-mini")
    openai_embedding_model: str = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    localhost_llm_base_url: str = os.getenv("LOCALHOST_LLM_BASE_URL", "http://localhost:11434/v1")
    localhost_default_model: str = os.getenv("LOCALHOST_DEFAULT_MODEL", "qwen2.5:7b")
    localhost_embedding_model: str = os.getenv("LOCALHOST_EMBEDDING_MODEL", "nomic-embed-text")
    runtime_default_provider: str = os.getenv("RUNTIME_DEFAULT_PROVIDER", "localhost")
    embedding_provider: str = os.getenv("EMBEDDING_PROVIDER", "openai")
    model_request_timeout_seconds: int = _as_int("MODEL_REQUEST_TIMEOUT_SECONDS", 60)
    embedding_retry_max_attempts: int = _as_int("EMBEDDING_RETRY_MAX_ATTEMPTS", 3)
    embedding_retry_backoff_seconds: int = _as_int("EMBEDDING_RETRY_BACKOFF_SECONDS", 30)


settings = Settings()
