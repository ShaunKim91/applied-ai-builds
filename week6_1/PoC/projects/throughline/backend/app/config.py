"""Central configuration for the Throughline backend.

All values are overridable via environment variables (see .env.example).
No secrets are ever hardcoded here — API keys are read at call-time from the
files referenced by *_api_key_file, which point at the read-only-mounted
`api_keys/` directory from the top-level lectures_projects repo.

Throughline is Fenwick Mutual's Policyholder Services contact-center
copilot (see docs/guide.html for the full "who this is for" narrative) — the
third product in the "Fenwick Mutual" suite alongside Week5_1's Verity
(claims research) and Week5_2's Threshold (guarded claims-payout agent).
It shares their "Fenwick Ledger" design system and commercial-grade security
architecture (this file's shape mirrors both products' config.py almost
exactly, deliberately — see architecture.md §0 for why reusing a proven
platform layer across a product family is itself a commercial-grade signal,
not a shortcut), but shares no code deployment: separate container,
separate database, separate port.

Unlike Verity/Threshold (agentic research / guarded action-taking),
Throughline's own axis is conversational continuity — real LangChain LCEL
chains, SQL-persisted dual-strategy memory, and memory-conditioned tool
calls — the one structural capability neither of its siblings has, because
neither has a notion of the same external counterparty (a policyholder)
recurring across separate sessions.
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_name: str = "Throughline"
    app_version: str = "1.0.0"
    org_name: str = "Fenwick Mutual"

    # --- Security (identical architecture to Verity's / Threshold's — see
    # that project's security.py for the full rationale) ---
    secret_key: str = "throughline-dev-secret-change-in-production"
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
    # A small, instruction-tuned open-weight model well-suited to running as
    # this app's shared local Runnable "brain" — with specific, verified
    # generation settings tuned for this exact model (see chains/llm_runnable.py).
    local_chat_model: str = "Qwen/Qwen2.5-0.5B-Instruct"

    # --- Memory governance (admin-editable at runtime, see models.MemorySetting) ---
    # Turns kept verbatim in the LCEL prompt window before older turns are
    # folded into a rolling summary — mirrors a common `history[-6:]` window
    # technique, doubled because Throughline also persists conversation
    # history (a typical baseline implementation of this pattern does not),
    # so a slightly larger live window is affordable.
    default_window_turns: int = 8
    # Real, pattern-based (not ML-based) redaction of common identifier
    # shapes before ANY persistence or cloud call — see ml/redaction.py for
    # the exact patterns and this project's explicit non-claim of certified
    # PII-detection accuracy.
    default_redaction_enabled: bool = True

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
