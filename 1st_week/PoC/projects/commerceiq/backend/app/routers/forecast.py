import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import models
from ..audit import log_action, timed
from ..config import settings
from ..database import get_db
from ..etl.online_retail import ensure_online_retail_daily
from ..ml import forecast as forecast_ml
from ..ml import llm as llm_ml
from ..security import get_current_user

router = APIRouter(prefix="/api/forecast", tags=["forecast"])


class ForecastRequest(BaseModel):
    horizon_days: int = Field(14, ge=7, le=60)
    use_openrouter: bool = False
    lang: str = "en"


@router.get("/datasets")
def datasets():
    return [
        {
            "id": "uci_online_retail",
            "name": "UCI Online Retail — Daily Revenue (UK, 2010-2011)",
            "source": "https://archive.ics.uci.edu/dataset/352/online+retail",
            "license": "CC BY 4.0",
        }
    ]


@router.get("/runs")
def recent_runs(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    runs = db.query(models.ForecastRun).order_by(models.ForecastRun.created_at.desc()).limit(10).all()
    return [
        {
            "id": r.id,
            "horizon_days": r.horizon_days,
            "mae": r.mae,
            "mape": r.mape,
            "smape": r.smape,
            "anomaly_count": r.anomaly_count,
            "insight_provider": r.insight_provider,
            "created_at": r.created_at.isoformat(),
        }
        for r in runs
    ]


@router.post("/run")
def run(
    payload: ForecastRequest,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    series = ensure_online_retail_daily(settings.data_dir)
    result = forecast_ml.run_forecast(series, horizon_days=payload.horizon_days)

    provider = "openrouter" if payload.use_openrouter else "local"
    lang_name = "Korean" if payload.lang == "ko" else "English"
    system = (
        "You are a retail operations analyst. Given a demand forecast summary, write a concise, "
        "business-readable insight (3-5 sentences) covering the trend direction, notable anomalies, "
        f"and one concrete, actionable recommendation. Respond only in {lang_name}."
    )
    anomaly_summary = (
        f"{len(result['anomalies'])} anomalies detected." if result["anomalies"] else "No significant anomalies."
    )
    # Prefer sMAPE in the prompt: it's always defined (bounded 0-200%), unlike
    # MAPE which we deliberately leave as None/partial when backtest days had
    # ~$0 actual revenue (see ml/forecast.py's mape_note) — citing a smaller,
    # always-sane number keeps the LLM's narrative from repeating a misleading
    # statistic if a $0-revenue day landed in the backtest window.
    accuracy_desc = f"sMAPE={result['metrics']['smape']}%"
    if result["metrics"]["mape"] is not None:
        accuracy_desc += f" (MAPE={result['metrics']['mape']}%)"
    user_msg = (
        f"Forecast horizon: {payload.horizon_days} days. "
        f"Backtest MAE={result['metrics']['mae']}, {accuracy_desc}. {anomaly_summary} "
        f"Last known daily revenue: {result['history'][-1]['value']:.2f}. "
        f"First forecast value: {result['forecast'][0]['value']:.2f}. "
        f"Last forecast value: {result['forecast'][-1]['value']:.2f}."
    )

    try:
        with timed() as elapsed:
            gen = llm_ml.generate(system, user_msg, provider=provider)
        latency = elapsed()
        insight, used_provider = gen["text"], gen["provider"]
        status = "success"
    except Exception as exc:
        insight = f"(AI insight unavailable: {exc})"
        used_provider, latency, status = provider, 0.0, "failed"

    record = models.ForecastRun(
        owner_id=user.id,
        dataset="uci_online_retail",
        horizon_days=payload.horizon_days,
        mae=result["metrics"]["mae"] or 0.0,
        mape=result["metrics"]["mape"],
        smape=result["metrics"]["smape"] or 0.0,
        anomaly_count=len(result["anomalies"]),
        ai_insight=insight,
        insight_provider=used_provider,
        result_json=json.dumps(result),
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    model_used = settings.openrouter_model if used_provider == "openrouter" else settings.local_llm_model
    log_action(db, user, "forecast.run", model_used=model_used, detail=f"horizon={payload.horizon_days}", latency_ms=latency, status=status)

    return {**result, "ai_insight": insight, "insight_provider": used_provider, "run_id": record.id}
