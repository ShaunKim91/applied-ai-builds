"""VoxIQ — FastAPI entrypoint.

Responsibilities on startup:
  1. Create SQL tables (SQLAlchemy metadata) if they don't exist yet.
  2. Seed the admin account (idempotent).
  3. Kick off a *background* thread that downloads the public datasets,
     indexes the FOMC minutes archive, and warms every local AI model into
     memory — each step isolated in its own try/except (see the Week1 PoC's
     debug/issue-06: an unrelated step's failure must never take the others
     down with it). /api/health responds immediately regardless; use
     /api/health/ready or /api/admin/system for live model-loaded status.

Also serves the built React frontend (frontend/dist, copied to
/app/frontend_dist by the Docker build) as static files, with a catch-all
route so client-side (React Router) refreshes don't 404.
"""
import logging
import os
import threading

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import models, state
from .config import settings
from .database import Base, SessionLocal, engine
from .routers import admin, auth, health, meetings, sandbox, search, tokenizer
from .security import hash_password

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("voxiq")

app = FastAPI(title=settings.app_name, version=settings.app_version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for sub in ("uploads", "sample_audio", "fomc_minutes", "chroma"):
    os.makedirs(os.path.join(settings.data_dir, sub), exist_ok=True)

Base.metadata.create_all(bind=engine)


def _seed_admin() -> None:
    db = SessionLocal()
    try:
        existing = db.query(models.User).filter(models.User.email == settings.admin_email).first()
        if not existing:
            db.add(
                models.User(
                    email=settings.admin_email,
                    hashed_password=hash_password(settings.admin_password),
                    display_name="Administrator",
                    role="admin",
                )
            )
            db.commit()
            logger.info("Seeded admin user: %s", settings.admin_email)
    finally:
        db.close()


def _warm_step(name: str, fn) -> bool:
    """Runs one bootstrap step in isolation — see Week1 PoC's
    debug/issue-06 for why this matters (a transient network failure in one
    step must never silently skip the others)."""
    try:
        fn()
        state.bootstrap_step_errors.pop(name, None)
        return True
    except Exception as exc:  # noqa: BLE001
        state.bootstrap_step_errors[name] = str(exc)
        logger.exception("Bootstrap step failed: %s (will retry lazily on first real request instead)", name)
        return False


def _warm_cache() -> None:
    logger.info("Bootstrap: downloading public datasets ...")
    from .etl.audio_samples import ensure_sample_audio
    from .routers.search import index_fomc_minutes

    ok_audio = _warm_step("dataset:sample_audio", lambda: ensure_sample_audio(settings.data_dir))
    ok_fomc = _warm_step("dataset:fomc_minutes+index", index_fomc_minutes)
    logger.info("Bootstrap: dataset step done (audio=%s, fomc=%s). Warming AI models ...", ok_audio, ok_fomc)

    from .ml import embeddings, llm, reranker, tokenizer_explorer, whisper_asr

    logger.info("  loading embedding model (%s) ...", settings.embedding_model)
    _warm_step("model:embeddings", embeddings.dimension)
    logger.info("  loading reranker model (%s) ...", settings.reranker_model)
    _warm_step("model:reranker", reranker.model_info)
    logger.info("  loading whisper model (%s) ...", settings.whisper_model)
    _warm_step("model:whisper", whisper_asr.model_info)
    logger.info("  loading local LLM (%s) ...", settings.local_llm_model)
    _warm_step("model:local_llm", llm.local_model_info)
    logger.info("  loading tokenizer explorer model (%s) ...", settings.tokenizer_model)
    _warm_step("model:tokenizer_explorer", tokenizer_explorer.model_info)

    if state.bootstrap_step_errors:
        logger.warning(
            "Bootstrap finished with %d failed step(s): %s — each will be retried automatically the "
            "first time a request actually needs it.",
            len(state.bootstrap_step_errors),
            list(state.bootstrap_step_errors),
        )
    else:
        logger.info("Bootstrap: all datasets + models warm. VoxIQ is fully ready.")
    state.bootstrap_complete.set()


@app.on_event("startup")
def on_startup() -> None:
    _seed_admin()
    threading.Thread(target=_warm_cache, daemon=True).start()


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(meetings.router)
app.include_router(search.router)
app.include_router(sandbox.router)
app.include_router(tokenizer.router)
app.include_router(admin.router)

app.mount("/media", StaticFiles(directory=settings.data_dir), name="media")

FRONTEND_DIST = os.environ.get("FRONTEND_DIST", "/app/frontend_dist")
if os.path.isdir(FRONTEND_DIST):
    assets_dir = os.path.join(FRONTEND_DIST, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str):
        candidate = os.path.join(FRONTEND_DIST, full_path)
        if full_path and os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))
else:
    logger.warning("Frontend build not found at %s — API-only mode.", FRONTEND_DIST)
