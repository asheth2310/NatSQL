"""Application settings, overridable via environment variables or a .env file."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the backend/ directory (or project root) if present.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")


def _bool_env(name: str, default: bool | None = None) -> bool | None:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    def __init__(self) -> None:
        # --- Database (read-only role) ---
        self.db_host: str = os.getenv("NATSQL_DB_HOST", "127.0.0.1")
        self.db_port: int = int(os.getenv("NATSQL_DB_PORT", "3307"))
        self.db_user: str = os.getenv("NATSQL_DB_USER", "natsql_ro")
        self.db_password: str = os.getenv("NATSQL_DB_PASSWORD", "natsql_ro_pass")
        self.db_name: str = os.getenv("NATSQL_DB_NAME", "demo")

        # --- LLM ---
        self.ollama_url: str = os.getenv("NATSQL_OLLAMA_URL", "http://localhost:11434")
        self.ollama_model: str = os.getenv("NATSQL_OLLAMA_MODEL", "qwen2.5-coder:7b")
        # None = auto-detect (use Ollama if reachable, else fallback engine)
        self.ollama_enabled: bool | None = _bool_env("NATSQL_OLLAMA_ENABLED")
        self.llm_timeout_s: float = float(os.getenv("NATSQL_LLM_TIMEOUT_S", "60"))
        self.llm_temperature: float = float(os.getenv("NATSQL_LLM_TEMPERATURE", "0.1"))

        # --- Safety ---
        self.max_rows: int = int(os.getenv("NATSQL_MAX_ROWS", "100"))
        self.query_timeout_ms: int = int(os.getenv("NATSQL_QUERY_TIMEOUT_MS", "5000"))
        self.max_retries: int = int(os.getenv("NATSQL_MAX_RETRIES", "1"))

        # --- Server ---
        self.host: str = os.getenv("NATSQL_HOST", "0.0.0.0")
        self.port: int = int(os.getenv("NATSQL_PORT", "8000"))


settings = Settings()
