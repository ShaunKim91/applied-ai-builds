"""Time-series forecasting + anomaly detection.

Applies standard techniques (seasonal decomposition, Holt-Winters triple
exponential smoothing, deseasonalized-residual anomaly detection) — commonly
introduced on classic toy series like AirPassengers — to real commercial
data (UCI Online Retail daily revenue). No AI model here — classic
statistics — which is a deliberate design point: not every "intelligence"
feature needs an LLM.
"""
import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.seasonal import seasonal_decompose


def run_forecast(series: pd.Series, horizon_days: int = 14, seasonal_periods: int = 7) -> dict:
    series = series.asfreq("D").interpolate().clip(lower=0)
    train = series

    model = ExponentialSmoothing(
        train,
        trend="add",
        seasonal="add",
        seasonal_periods=seasonal_periods,
        initialization_method="estimated",
    ).fit()

    # Backtest: refit on all-but-last-`horizon_days`, forecast the held-out
    # window, and score against the real values (walk-forward style, per the
    # standard "no shuffled train/test split for time series" rule).
    mae, mape, smape, mape_note = None, None, None, None
    if len(train) > seasonal_periods * 3 + horizon_days:
        bt_train, bt_test = train.iloc[:-horizon_days], train.iloc[-horizon_days:]
        bt_model = ExponentialSmoothing(
            bt_train,
            trend="add",
            seasonal="add",
            seasonal_periods=seasonal_periods,
            initialization_method="estimated",
        ).fit()
        bt_pred = bt_model.forecast(horizon_days)
        abs_err = np.abs(bt_test.values - bt_pred.values)
        mae = float(np.mean(abs_err))

        # MAPE is undefined/explosive when the actual value is 0 or near-0 —
        # a real case here, since this retailer has $0-revenue Saturdays
        # (see debug/issue-05). Standard practice: exclude those points from
        # MAPE and note how many were excluded, rather than silently
        # dividing by a placeholder 1 and reporting a misleading number.
        nonzero_mask = bt_test.values > 1.0
        excluded = int((~nonzero_mask).sum())
        if nonzero_mask.any():
            mape = float(np.mean(abs_err[nonzero_mask] / bt_test.values[nonzero_mask]) * 100)
        if excluded:
            mape_note = f"{excluded} of {horizon_days} backtest day(s) had ~$0 actual revenue and were excluded from MAPE (see sMAPE for a metric that handles this)."

        # sMAPE (symmetric MAPE, bounded 0-200%) as a companion metric that
        # doesn't blow up on near-zero actuals — recommended alongside MAE
        # given MAPE's well-known weaknesses.
        smape_denom = (np.abs(bt_test.values) + np.abs(bt_pred.values)) / 2
        smape_denom = np.where(smape_denom == 0, 1, smape_denom)
        smape = float(np.mean(abs_err / smape_denom) * 100)

    forecast = model.forecast(horizon_days)
    resid_std = float((train - model.fittedvalues).std())
    ci_lower = forecast - 1.96 * resid_std
    ci_upper = forecast + 1.96 * resid_std

    decomposition = seasonal_decompose(
        train, model="additive", period=seasonal_periods, extrapolate_trend="freq"
    )
    resid = decomposition.resid.dropna()
    threshold = 2.5 * float(resid.std())
    anomaly_mask = (resid - float(resid.mean())).abs() > threshold
    anomalies = [
        {"date": str(d.date()), "value": float(train.loc[d]), "residual": float(r)}
        for d, r in resid[anomaly_mask].items()
    ]

    return {
        "history": [{"date": str(d.date()), "value": float(v)} for d, v in train.items()],
        "forecast": [
            {"date": str(d.date()), "value": float(v), "lower": float(lo), "upper": float(hi)}
            for d, v, lo, hi in zip(forecast.index, forecast.values, ci_lower.values, ci_upper.values)
        ],
        "anomalies": anomalies,
        "metrics": {
            "mae": round(mae, 2) if mae is not None else None,
            "mape": round(mape, 2) if mape is not None else None,
            "smape": round(smape, 2) if smape is not None else None,
            "mape_note": mape_note,
        },
        "params": {
            "alpha": round(float(model.params["smoothing_level"]), 4),
            "beta": round(float(model.params["smoothing_trend"]), 4),
            "gamma": round(float(model.params["smoothing_seasonal"]), 4),
        },
    }
