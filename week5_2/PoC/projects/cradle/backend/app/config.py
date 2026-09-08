"""Central configuration for the Cradle backend.

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
    app_name: str = "Cradle"
    app_version: str = "1.0.0"

    # --- Security ---
    secret_key: str = "cradle-dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24

    # --- Storage ---
    database_url: str = "sqlite:////app/data/app.db"
    data_dir: str = "/app/data"
    chroma_persist_dir: str = "/app/data/chroma"

    # --- Local AI models ---
    embedding_model: str = "intfloat/multilingual-e5-small"
    embedding_dim: int = 384
    # A well-suited small instruction-tuned model for the ReAct agent's own
    # "brain" — also the same small local LLM validated across the
    # Week1-14_1 PoCs.
    local_agent_model: str = "Qwen/Qwen2.5-0.5B-Instruct"

    # --- Guardrail defaults (admin-editable at runtime, see models.GuardrailSetting) ---
    default_max_steps: int = 5
    default_cost_cap: int = 100
    # Per-tool cost units, plus this project's own two new tools
    # (issue_refund, delete_customer_data).
    default_tool_cost: dict[str, int] = {
        "calculator": 5,
        "get_today": 2,
        "convert_currency": 5,
        "lookup_faq": 10,
        "issue_refund": 30,
        "delete_customer_data": 50,
    }

    # --- Model routing (opt-in escalation to a larger cloud model — a
    # well-documented "small local model by default, escalate when needed"
    # pattern) ---
    llm_provider: str = "local"
    openrouter_api_key_file: str = "/app/secrets/openrouter.md"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "qwen/qwen3-8b"
    # An ESTIMATE, not a live-metered value: OpenRouter's chat-completions
    # API doesn't return a per-call dollar cost, so this is computed from
    # qwen3-8b's per-token list price verified live during this project's
    # Week1 PoC build ($0.117/M input, $0.455/M output tokens) against a
    # generously-rounded-up ~700 input + ~300 output tokens for one
    # escalation call. Tracked in the same spirit as Week5_1 Compass's own
    # documented-estimate cost ledger — never presented as an exact figure.
    openrouter_escalation_estimated_cost_usd: float = 0.0005
    openai_api_key_file: str = "/app/secrets/openai.md"
    anthropic_api_key_file: str = "/app/secrets/anthropic.md"
    gemini_api_key_file: str = "/app/secrets/gemini.md"

    # --- Cost governance (reused pattern from the Week5_1 "Compass" PoC) ---
    default_daily_budget_usd: float = 1.00

    # --- Seed admin account ---
    admin_email: str = "admin@cradle.local"
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
