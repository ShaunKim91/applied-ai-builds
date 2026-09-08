"""Compass — FastAPI entrypoint.

Responsibilities on startup:
  1. Create SQL tables (SQLAlchemy metadata) if they don't exist yet.
  2. Seed the admin account + default budget row (idempotent).
  3. Kick off a *background* thread that loads the embedding model, the
     reranker, the local LLM, and checks live web-search connectivity —
     each step isolated in its own try/except (the Week1-4 PoCs'
     `_warm_step()` pattern). /api/health responds immediately regardless;
     use /api/health/ready or /api/admin/system for live model status.

Unlike Week4's Lucent, there is no seed-corpus download/index step here —
this week's retrieval source is the live web, not a fixed local corpus.

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
from .routers import admin, archive, auth, grounding_lab, health, research, trend_radar
from .security import hash_password

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("compass")

app = FastAPI(title=settings.app_name, version=settings.app_version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs(os.path.join(settings.data_dir, "chroma"), exist_ok=True)

Base.metadata.create_all(bind=engine)


def _seed_admin_and_budget() -> None:
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
            logger.info("Seeded admin user: %s", settings.admin_email)
        if not db.get(models.BudgetSetting, 1):
            db.add(models.BudgetSetting(id=1, daily_limit_usd=settings.default_daily_budget_usd))
            logger.info("Seeded default daily budget: $%.2f", settings.default_daily_budget_usd)
        db.commit()
    finally:
        db.close()


def _warm_step(name: str, fn) -> bool:
    """Runs one bootstrap step in isolation — see Week4 PoC's debug/issue-01
    for a real, previously-encountered example of why this matters (an
    unrelated step's failure must never silently take another step down)."""
    try:
        fn()
        state.bootstrap_step_errors.pop(name, None)
        return True
    except Exception as exc:  # noqa: BLE001
        state.bootstrap_step_errors[name] = str(exc)
        logger.exception("Bootstrap step failed: %s (will retry lazily on first real request instead)", name)
        return False


def _warm_cache() -> None:
    from .ml import embeddings, llm, reranker
    from .search import web_search

    logger.info("Bootstrap: loading embedding model (%s) ...", settings.embedding_model)
    _warm_step("model:embeddings", embeddings.dimension)

    logger.info("Bootstrap: loading reranker model (%s) ...", settings.reranker_model)
    _warm_step("model:reranker", reranker.model_info)

    logger.info("Bootstrap: loading local LLM (%s) ...", settings.local_llm_model)
    _warm_step("model:local_llm", llm.local_model_info)

    logger.info("Bootstrap: checking live web-search connectivity (ddgs) ...")

    def _check_search():
        state.last_web_search_check = web_search.connectivity_check()

    _warm_step("search:connectivity", _check_search)
    logger.info("Bootstrap: web search mode = %s", (state.last_web_search_check or {}).get("mode"))

    if state.bootstrap_step_errors:
        logger.warning(
            "Bootstrap finished with %d failed step(s): %s — each will be retried automatically the "
            "first time a request actually needs it.",
            len(state.bootstrap_step_errors),
            list(state.bootstrap_step_errors),
        )
    else:
        logger.info("Bootstrap: all models warm, web search reachable. Compass is fully ready.")
    state.bootstrap_complete.set()


@app.on_event("startup")
def on_startup() -> None:
    _seed_admin_and_budget()
    threading.Thread(target=_warm_cache, daemon=True).start()


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(research.router)
app.include_router(archive.router)
app.include_router(grounding_lab.router)
app.include_router(trend_radar.router)
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
