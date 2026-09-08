"""Central configuration for the VoxIQ backend.

All values are overridable via environment variables (see .env.example).
No secrets are ever hardcoded here — API keys are read at call-time from the
files referenced by *_api_key_file, which point at the read-only-mounted
`api_keys/` directory from the top-level lectures_projects repo.
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_name: str = "VoxIQ"
    app_version: str = "1.0.0"

    # --- Security ---
    secret_key: str = "voxiq-dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24

    # --- Storage ---
    database_url: str = "sqlite:////app/data/app.db"
    data_dir: str = "/app/data"
    chroma_persist_dir: str = "/app/data/chroma"

    # --- Local AI models (HuggingFace model ids, downloaded on first use) ---
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    whisper_model: str = "tiny"
    local_llm_model: str = "Qwen/Qwen2.5-0.5B-Instruct"
    tokenizer_model: str = "gpt2"

    # --- LLM provider routing (used by the Analytics Agent's code generator) ---
    # "local" (default, no key needed) or "openrouter" (validated this round).
    # "openai" / "anthropic" / "gemini" are scaffolded for future use but are
    # NOT validated in this build — calling them raises NotImplementedError.
    llm_provider: str = "local"

    openrouter_api_key_file: str = "/app/secrets/openrouter.md"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "qwen/qwen3-8b"

    openai_api_key_file: str = "/app/secrets/openai.md"
    anthropic_api_key_file: str = "/app/secrets/anthropic.md"
    gemini_api_key_file: str = "/app/secrets/gemini.md"

    # --- Code sandbox routing ---
    # "local" (default, always available) — subprocess with resource limits
    # and a restricted builtins set. "e2b" is scaffolded (config field only)
    # but NOT validated this round — this repo has no E2B API key.
    sandbox_provider: str = "local"
    e2b_api_key_file: str = "/app/secrets/e2b.md"
    sandbox_timeout_seconds: int = 10
    sandbox_max_memory_mb: int = 256

    # --- Seed admin account (change via .env for real deployments) ---
    admin_email: str = "admin@voxiq.local"
    admin_password: str = "ChangeMe123!"


settings = Settings()


def read_key_file(path: str | None) -> str | None:
    """Read an API key from a file reference. Returns None if missing/empty.

    Keys are NEVER read from environment variables or source code directly —
    only from files, per the project convention of referencing
    `api_keys/*.md` instead of embedding secrets.
    """
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        return None
    content = p.read_text(encoding="utf-8").strip()
    return content or None
