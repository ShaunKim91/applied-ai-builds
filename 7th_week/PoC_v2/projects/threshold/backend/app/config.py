"""Central configuration for the Threshold backend.

All values are overridable via environment variables (see .env.example).
No secrets are ever hardcoded here — API keys are read at call-time from the
files referenced by *_api_key_file, which point at the read-only-mounted
`api_keys/` directory from the top-level lectures_projects repo.

Threshold is Fenwick Mutual's claims-processing agent console (see
docs/guide.html for the full "who this is for" narrative) — a from-scratch,
commercial-grade rebuild of the Week7 "Cradle" PoC, sharing the
"Fenwick Ledger" design system and security architecture with its Week6
companion, Verity, but not sharing any code deployment (separate container,
separate database, separate port).
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_name: str = "Threshold"
    app_version: str = "1.0.0"
    org_name: str = "Fenwick Mutual"

    # --- Security (identical architecture to Verity's — see that project's
    # security.py for the full rationale) ---
    secret_key: str = "threshold-dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 20
    refresh_token_expire_days: int = 7
    admin_email: str = "admin@fenwickmutual.example"
    admin_password: str = "ChangeMe123!"
    enforce_secure_defaults: bool = False
    cookie_secure: bool = False

    # --- Account lockout ---
    max_failed_logins: int = 5
    lockout_minutes: int = 15

    # --- Rate limiting (single-process, see rate_limit.py) ---
    rate_limit_auth_per_minute: int = 20
    rate_limit_ai_per_minute: int = 20

    # --- Storage ---
    database_url: str = "sqlite:////app/data/app.db"
    data_dir: str = "/app/data"
    chroma_persist_dir: str = "/app/data/chroma"

    # --- Local AI models ---
    embedding_model: str = "intfloat/multilingual-e5-small"
    embedding_dim: int = 384
    # A small, openly-licensed instruct model well suited to running as the
    # ReAct agent's local "brain" with reliable tool-calling behavior.
    local_agent_model: str = "Qwen/Qwen2.5-0.5B-Instruct"

    # --- Guardrail defaults (admin-editable at runtime, see models.GuardrailSetting) ---
    default_max_steps: int = 6
    default_cost_cap: int = 150
    # Per-tool cost units, themed for claims processing. See architecture.md
    # §2 for the full risk-tier/cost-rationale table.
    default_tool_cost: dict[str, int] = {
        "check_filing_deadline": 2,
        "lookup_policy_coverage": 5,
        "estimate_claim_payout": 5,
        "convert_reinsurance_currency": 5,
        "lookup_claims_procedure": 10,
        "issue_claim_payout": 35,
        "close_and_purge_claim_file": 50,
    }
    # Amount-aware HITL threshold — a real engineering upgrade over the old
    # Cradle PoC's flat per-tool-name HITL gate: issue_claim_payout only
    # pauses for approval when the requested amount EXCEEDS this threshold,
    # not unconditionally. Explicitly illustrative/fictional, not a real
    # Fenwick Mutual policy figure.
    payout_approval_threshold_usd: float = 2500.0

    # --- Model routing (opt-in escalation to a larger cloud model) ---
    openrouter_api_key_file: str = "/app/secrets/openrouter.md"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "qwen/qwen3-8b"
    # ESTIMATE, not a live-metered value — same documented-estimate pattern
    # as every prior PoC's own OpenRouter cost ledger.
    openrouter_escalation_estimated_cost_usd: float = 0.0005
    openai_api_key_file: str = "/app/secrets/openai.md"
    anthropic_api_key_file: str = "/app/secrets/anthropic.md"
    gemini_api_key_file: str = "/app/secrets/gemini.md"

    # --- Cost governance (org-scoped) ---
    default_daily_budget_usd: float = 1.00

    # --- Metrics ---
    metrics_window_size: int = 500


settings = Settings()


def read_key_file(path: str | None) -> str | None:
    """Read an API key from a file reference. Returns None if missing/empty."""
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        return None
    content = p.read_text(encoding="utf-8").strip()
    return content or None
