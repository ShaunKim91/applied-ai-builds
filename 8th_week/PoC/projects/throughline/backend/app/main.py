"""Throughline — entrypoint: startup bootstrap (with a production insecure-
defaults guard), request correlation ID + latency middleware, a global
structured-error handler, and SPA static serving."""
import logging
import sys
import threading
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import models, state
from .chains.llm_runnable import local_model_info
from .config import settings
from .database import SessionLocal, engine
from .metrics import new_request_id, record_latency
from .ml import embeddings
from .routers import admin, auth, cases, health, status
from .security import hash_password

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] throughline: %(message)s")
logger = logging.getLogger("throughline")

if settings.enforce_secure_defaults:
    insecure = []
    if settings.secret_key == "throughline-dev-secret-change-in-production":
        insecure.append("SECRET_KEY")
    if settings.admin_password == "ChangeMe123!":
        insecure.append("ADMIN_PASSWORD")
    if insecure:
        logger.error("Refusing to start in production with insecure default(s): %s. Set real values via .env.", ", ".join(insecure))
        sys.exit(1)

models.Base.metadata.create_all(bind=engine)


def _seed() -> None:
    db = SessionLocal()
    try:
        org = db.query(models.Organization).first()
        if not org:
            org = models.Organization(name=settings.org_name)
            db.add(org)
            db.commit()
            db.refresh(org)
            logger.info("Seeded organization: %s", org.name)
        if not db.query(models.User).filter(models.User.email == settings.admin_email).first():
            admin_user = models.User(org_id=org.id, email=settings.admin_email, hashed_password=hash_password(settings.admin_password), display_name="Admin", role="admin")
            db.add(admin_user)
            logger.info("Seeded admin user: %s", settings.admin_email)
        if not db.query(models.BudgetSetting).filter(models.BudgetSetting.org_id == org.id).first():
            db.add(models.BudgetSetting(org_id=org.id, daily_limit_usd=settings.default_daily_budget_usd))
            logger.info("Seeded default daily budget: $%.2f", settings.default_daily_budget_usd)
        if not db.query(models.MemorySetting).filter(models.MemorySetting.org_id == org.id).first():
            db.add(models.MemorySetting(org_id=org.id, window_turns=settings.default_window_turns, redaction_enabled=settings.default_redaction_enabled))
            logger.info("Seeded default memory settings: window_turns=%d redaction_enabled=%s", settings.default_window_turns, settings.default_redaction_enabled)
        db.commit()
    finally:
        db.close()


_seed()

app = FastAPI(title="Throughline")


@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or new_request_id()
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception as exc:  # noqa: BLE001
        db = SessionLocal()
        try:
            db.add(models.ErrorLog(request_id=request_id, route=request.url.path, method=request.method, error_class=type(exc).__name__, message=str(exc)[:2000]))
            db.commit()
        finally:
            db.close()
        logger.exception("Unhandled error [%s] on %s %s", request_id, request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "An unexpected error occurred.", "request_id": request_id})
    latency_ms = (time.perf_counter() - start) * 1000
    record_latency(request.url.path, latency_ms)
    response.headers["X-Request-ID"] = request_id
    return response


def _warm_step(name: str, fn) -> bool:
    try:
        fn()
        state.set_model_warm(name, True)
        return True
    except Exception:
        logger.exception("Bootstrap step failed: %s (will retry lazily on first real request instead)", name)
        state.set_step_error(name, "failed to load — will retry on first use")
        return False


def _warm_cache() -> None:
    logger.info("Bootstrap: loading embedding model (%s) ...", settings.embedding_model)
    _warm_step("embeddings", embeddings.dimension)
    logger.info("Bootstrap: loading local chat LLM (%s) ...", settings.local_chat_model)
    _warm_step("local_agent", local_model_info)
    state.mark_bootstrap_complete()
    ready = state.readiness()
    if ready["all_warm"]:
        logger.info("Bootstrap: all models warm. Throughline is fully ready.")
    else:
        logger.warning("Bootstrap finished with failed step(s): %s — each retries lazily on first real request.", ready["bootstrap_step_errors"])


threading.Thread(target=_warm_cache, daemon=True).start()

app.include_router(health.router)
app.include_router(status.router)
app.include_router(auth.router)
app.include_router(cases.router)
app.include_router(admin.router)

_frontend_dist = Path(__file__).resolve().parent.parent / "frontend_dist"
if _frontend_dist.exists():
    app.mount("/assets", StaticFiles(directory=_frontend_dist / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def spa(full_path: str):
        candidate = _frontend_dist / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_frontend_dist / "index.html")
