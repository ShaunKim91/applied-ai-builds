"""Central configuration for the Parchment backend.

All values are overridable via environment variables (see .env.example).
No secrets are ever hardcoded here — API keys are read at call-time from the
files referenced by *_api_key_file, which point at the read-only-mounted
`api_keys/` directory at the top of the repository.
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_name: str = "Parchment"
    app_version: str = "1.0.0"

    # --- Security ---
    secret_key: str = "parchment-dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24

    # --- Storage ---
    database_url: str = "sqlite:////app/data/app.db"
    data_dir: str = "/app/data"
    chroma_persist_dir: str = "/app/data/chroma"

    # --- Local AI models (HuggingFace model ids, downloaded on first use) ---
    # OCR uses the system `tesseract` binary via pytesseract — no HF model id;
    # its "model" is the LSTM traineddata bundled with the tesseract-ocr /
    # tesseract-ocr-kor apt packages installed in docker/Dockerfile.
    vlm_model: str = "HuggingFaceTB/SmolVLM-256M-Instruct"
    local_llm_model: str = "Qwen/Qwen2.5-0.5B-Instruct"
    summarizer_model: str = "sshleifer/distilbart-cnn-12-6"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # --- LLM provider routing (used for OCR-text structuring + PDF/table insight) ---
    # "local" (default, no key needed) or "openrouter" (validated this round).
    # "openai" / "anthropic" / "gemini" are scaffolded for future use but are
    # NOT validated in this build — calling them raises NotImplementedError.
    # Gemini specifically is a common choice for this kind of image/document
    # extraction task (`google-genai`, model id `gemini-2.5-flash`) — named
    # here for parity, but per this build's brief, OpenRouter is the only
    # cloud API validated this round.
    llm_provider: str = "local"

    openrouter_api_key_file: str = "/app/secrets/openrouter.md"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "qwen/qwen3-8b"

    openai_api_key_file: str = "/app/secrets/openai.md"
    anthropic_api_key_file: str = "/app/secrets/anthropic.md"
    gemini_api_key_file: str = "/app/secrets/gemini.md"

    # --- Duplicate-document detection (embedding similarity, NOT RAG/search —
    # see architecture.md for why this is deliberately scoped narrowly and
    # doesn't grow into a full retrieve-then-answer search feature) ---
    dedupe_similarity_threshold: float = 0.90

    # --- PDF handling ---
    # 500 words/chunk (up from an initial 220 — see debug/issue-01): fewer,
    # larger chunks means each of the summarizer's sampled chunks covers
    # more of a long document, and produces fewer total pipeline calls.
    pdf_chunk_size_words: int = 500
    pdf_chunk_overlap_words: int = 60
    # If pypdf extracts fewer than this many characters, the PDF is treated
    # as a scanned/image-only PDF and falls back to pdf2image + Tesseract OCR.
    pdf_scanned_fallback_char_threshold: int = 40

    # --- Seed admin account (change via .env for real deployments) ---
    admin_email: str = "admin@parchment.local"
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
