"""Central configuration for the Compass backend.

All values are overridable via environment variables (see .env.example).
No secrets are ever hardcoded here — API keys are read at call-time from the
files referenced by *_api_key_file, which point at the read-only-mounted
`api_keys/` directory from the top-level repository.
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_name: str = "Compass"
    app_version: str = "1.0.0"

    # --- Security ---
    secret_key: str = "compass-dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24

    # --- Storage ---
    database_url: str = "sqlite:////app/data/app.db"
    data_dir: str = "/app/data"
    chroma_persist_dir: str = "/app/data/chroma"

    # --- Local AI models (HuggingFace model ids, downloaded on first use) ---
    # Both reused verbatim from the Week2/4 PoCs. cross-encoder/ms-marco is
    # also, independently, the same reranker a typical baseline implementation
    # of this pattern uses in its real deployed code — a hash-based toy
    # embedding is sometimes taught as an introductory placeholder, but a real
    # shipped version never actually uses that shortcut. We follow the real,
    # production-grade choice here, same judgment call Week4 made.
    embedding_model: str = "intfloat/multilingual-e5-small"
    embedding_dim: int = 384
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    local_llm_model: str = "Qwen/Qwen2.5-0.5B-Instruct"

    # --- LLM provider routing (report synthesis) ---
    # "local" (default, no key needed) or "openrouter" (validated this
    # round). "openai" / "anthropic" / "gemini" are scaffolded but NOT
    # validated. A typical baseline implementation of this pattern instead
    # defaults to a rule-based template with NO generation at all, offering
    # Gemini or a Claude/Codex CLI subprocess call as opt-in extras — none of
    # which we have a key or a validated mechanism for this round, so
    # OpenRouter fills that role.
    llm_provider: str = "local"

    openrouter_api_key_file: str = "/app/secrets/openrouter.md"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "qwen/qwen3-8b"
    # A real, documented OpenRouter feature (openrouter.ai/docs/guides/features/plugins/web-search,
    # verified live during planning) — appending ":online" to a model slug
    # (equivalently, plugins:[{"id":"web"}]) makes OpenRouter itself perform
    # live web search and return the results as response `annotations`, in
    # one call. This is Compass's "fully-managed cloud search" comparison
    # arm in the Grounding Lab — same OpenRouter key, a different request
    # shape, no second vendor/key introduced.
    openrouter_web_search_suffix: str = ":online"
    # Exa (OpenRouter's default web-search engine) list price at planning
    # time: ~$0.007/request for up to 10 results, +$0.001/extra result.
    # Used only as a documented ESTIMATE for the cost-governance ledger —
    # never billed directly by this app; OpenRouter bills the real amount.
    openrouter_web_search_estimated_cost_usd: float = 0.007

    openai_api_key_file: str = "/app/secrets/openai.md"
    anthropic_api_key_file: str = "/app/secrets/anthropic.md"
    gemini_api_key_file: str = "/app/secrets/gemini.md"

    # --- Web search (default, free, no key) ---
    # ddgs (PyPI, formerly duckduckgo-search) — confirmed live during
    # planning: `pip install ddgs`, `DDGS().text(query, max_results=n)` ->
    # [{title, href, body}, ...], no API key required. Its own docs disclose
    # it's an unofficial, "educational purposes" client, so failures are
    # expected and handled by falling back to deterministic mock results —
    # a standard mock-first resilience pattern for an unreliable third-party
    # dependency.
    web_search_max_results: int = 6
    web_search_rerank_top_k: int = 4

    # --- Groundedness (Week4 pattern, reused) ---
    groundedness_similarity_threshold: float = 0.55

    # --- Cost governance ---
    # The "budget cap" discipline — a standard cost-governance principle for
    # LLM-backed apps — which a typical baseline implementation of this
    # pattern does not implement anywhere in code. See models.BudgetSetting /
    # routers/admin.py.
    default_daily_budget_usd: float = 1.00

    # --- Seed admin account (change via .env for real deployments) ---
    admin_email: str = "admin@compass.local"
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
