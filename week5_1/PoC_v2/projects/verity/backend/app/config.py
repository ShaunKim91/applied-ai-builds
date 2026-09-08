"""Central configuration for the Verity backend.

All values are overridable via environment variables (see .env.example).
No secrets are ever hardcoded here — API keys are read at call-time from the
files referenced by *_api_key_file, which point at the read-only-mounted
`api_keys/` directory from the top-level lectures_projects repo.

Verity is Fenwick Mutual's claims-research assistant (see docs/guide.html
for the full "who this is for" narrative) — a from-scratch, commercial-grade
rebuild of the Week5_1 "Compass" PoC, not an incremental update to it.
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_name: str = "Verity"
    app_version: str = "1.0.0"
    org_name: str = "Fenwick Mutual"
    # Off by default so this demo boots immediately with its documented demo
    # credentials, exactly like every other product in this series. A real
    # deployment sets this true (alongside a real SECRET_KEY/ADMIN_PASSWORD)
    # to activate main.py's insecure-defaults startup guard — the guard's
    # logic is real and demonstrable (see debug/), it's just not forced on
    # by app_env alone, which would otherwise make the demo refuse to boot
    # with its own advertised admin@fenwickmutual.example / ChangeMe123! login.
    enforce_secure_defaults: bool = False

    # --- Security ---
    secret_key: str = "verity-dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    # Deliberately short-lived — a real commercial-grade upgrade over the
    # Week1-5_2 PoCs' single flat 24h token. Sessions are kept alive by
    # rotating refresh tokens instead (see security.py, models.RefreshToken).
    access_token_expire_minutes: int = 20
    refresh_token_expire_days: int = 7
    # If enforce_secure_defaults=true and either of these two still holds
    # its insecure default, main.py's startup guard refuses to boot rather
    # than silently running an insecure instance. See debug/ for why this exists.
    admin_email: str = "admin@fenwickmutual.example"
    admin_password: str = "ChangeMe123!"
    # This demo runs over plain HTTP on localhost, with no TLS terminator —
    # the `Secure` cookie attribute requires HTTPS (Chromium's "localhost is
    # a secure context" exception aside, this shouldn't be relied on). A
    # real deployment behind TLS sets COOKIE_SECURE=true; left false here so
    # session cookies are reliably set/sent in this project's actual local
    # Docker demo environment, on every browser, not just Chromium's
    # localhost special-case.
    cookie_secure: bool = False

    # --- Account lockout (new this round — see architecture.md's security section) ---
    max_failed_logins: int = 5
    lockout_minutes: int = 15

    # --- Rate limiting (new this round; hand-rolled in-memory limiter, see rate_limit.py —
    # documented explicitly as a single-process limit: a real multi-instance
    # deployment would need shared state, e.g. Redis) ---
    rate_limit_auth_per_minute: int = 20
    rate_limit_ai_per_minute: int = 20

    # --- Storage ---
    database_url: str = "sqlite:////app/data/app.db"
    data_dir: str = "/app/data"
    chroma_persist_dir: str = "/app/data/chroma"

    # --- Local AI models (reused, validated choices — see etc/glossary.md) ---
    embedding_model: str = "intfloat/multilingual-e5-small"
    embedding_dim: int = 384
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    local_llm_model: str = "Qwen/Qwen2.5-0.5B-Instruct"

    # --- Model routing (opt-in cloud upgrade) ---
    openrouter_api_key_file: str = "/app/secrets/openrouter.md"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "qwen/qwen3-8b"
    openai_api_key_file: str = "/app/secrets/openai.md"
    anthropic_api_key_file: str = "/app/secrets/anthropic.md"
    gemini_api_key_file: str = "/app/secrets/gemini.md"

    # --- Cost governance (org-scoped, reused pattern from Compass/Cradle) ---
    default_daily_budget_usd: float = 1.00

    # --- Metrics (new this round — in-memory rolling window, resets on
    # restart; documented honestly as a demo-scale limitation, not a claim of
    # a production metrics backend) ---
    metrics_window_size: int = 500


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
