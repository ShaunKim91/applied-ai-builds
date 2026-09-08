"""Lightweight, in-process observability: per-route rolling-window latency
percentiles and request-correlation IDs.

Explicitly NOT a claim of a production metrics stack (no Prometheus/
Grafana/OpenTelemetry) — this is documented as a demo-scale limitation: the
window is in-memory and resets on restart. What it genuinely provides that
no prior product in this series had: real p50/p95/p99 numbers computed from
actual request timings, not just a request counter.
"""
import uuid
from collections import defaultdict, deque

from .config import settings

_latencies: dict[str, deque] = defaultdict(lambda: deque(maxlen=settings.metrics_window_size))


def record_latency(route: str, ms: float) -> None:
    _latencies[route].append(ms)


def _percentile(sorted_values: list[float], pct: float) -> float:
    if not sorted_values:
        return 0.0
    idx = min(len(sorted_values) - 1, int(round(pct / 100 * (len(sorted_values) - 1))))
    return sorted_values[idx]


def snapshot() -> list[dict]:
    out = []
    for route, values in _latencies.items():
        if not values:
            continue
        ordered = sorted(values)
        out.append(
            {
                "route": route,
                "count": len(ordered),
                "p50_ms": round(_percentile(ordered, 50), 1),
                "p95_ms": round(_percentile(ordered, 95), 1),
                "p99_ms": round(_percentile(ordered, 99), 1),
            }
        )
    return sorted(out, key=lambda r: r["route"])


def new_request_id() -> str:
    return uuid.uuid4().hex[:16]
