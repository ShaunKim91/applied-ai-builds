"""CommerceIQ — FastAPI entrypoint.

Responsibilities on startup:
  1. Create SQL tables (SQLAlchemy metadata) if they don't exist yet.
  2. Seed the admin account (idempotent).
  3. Kick off a *background* thread that downloads the public datasets and
     warms every local AI model into memory, so the very first real user
     request isn't the slowest one. /api/health responds immediately
     regardless (it only proves the API+DB are alive); use
     /api/admin/system to see live model-loaded status.

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
from .routers import admin, auth, forecast, generate, health, search, vision
from .security import hash_password

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("commerceiq")

app = FastAPI(title=settings.app_name, version=settings.app_version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for sub in ("uploads", "generated", "sample_images", "raw", "processed", "chroma"):
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
    """Runs one bootstrap step in isolation. A failure here is logged and
    recorded per-step, but never prevents the remaining steps from running —
    see debug/issue-06 for the incident (a transient DNS failure fetching
    the UCI dataset) that this isolation was added to fix: previously one
    failed network call could silently skip warming all 4 AI models too,
    even though they have nothing to do with that dataset."""
    try:
        fn()
        state.bootstrap_step_errors.pop(name, None)
        return True
    except Exception as exc:  # noqa: BLE001 — any single step's failure must not abort the others
        state.bootstrap_step_errors[name] = str(exc)
        logger.exception("Bootstrap step failed: %s (will retry lazily on first real request instead)", name)
        return False


def _warm_cache() -> None:
    logger.info("Bootstrap: downloading public datasets ...")
    from .etl.online_retail import ensure_online_retail_daily
    from .etl.sample_catalog import ensure_sample_images

    ok_retail = _warm_step("dataset:online_retail", lambda: ensure_online_retail_daily(settings.data_dir))
    ok_samples = _warm_step("dataset:sample_catalog", lambda: ensure_sample_images(settings.data_dir))
    logger.info(
        "Bootstrap: dataset step done (online_retail=%s, sample_catalog=%s). Warming AI models ...",
        ok_retail,
        ok_samples,
    )

    from .ml import diffusion, embeddings, llm, vision

    logger.info("  loading vision model (%s) ...", settings.vit_model)
    _warm_step("model:vision", vision.model_info)
    logger.info("  loading embedding model (%s) ...", settings.embedding_model)
    _warm_step("model:embeddings", embeddings.dimension)
    logger.info("  loading local LLM (%s) ...", settings.local_llm_model)
    _warm_step("model:local_llm", llm.local_model_info)
    logger.info("  loading diffusion pipeline (%s) ...", settings.diffusion_model)
    _warm_step("model:diffusion", diffusion.model_info)

    if state.bootstrap_step_errors:
        logger.warning(
            "Bootstrap finished with %d failed step(s): %s — each will be retried automatically the "
            "first time a request actually needs it.",
            len(state.bootstrap_step_errors),
            list(state.bootstrap_step_errors),
        )
    else:
        logger.info("Bootstrap: all datasets + models warm. CommerceIQ is fully ready.")
    state.bootstrap_complete.set()


@app.on_event("startup")
def on_startup() -> None:
    _seed_admin()
    threading.Thread(target=_warm_cache, daemon=True).start()


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(vision.router)
app.include_router(generate.router)
app.include_router(forecast.router)
app.include_router(search.router)
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
