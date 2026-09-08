"""Bootstrap/readiness state — the same `_warm_step()` isolation pattern
validated across every prior product in this series (a failed model-load
step is logged and retried lazily on first real use, never cascades into
failing the other steps or the container's health check)."""
import threading

_lock = threading.Lock()
_models_warm: dict[str, bool] = {"embeddings": False, "reranker": False, "local_llm": False}
_bootstrap_complete = threading.Event()
_step_errors: dict[str, str] = {}
_search_mode = "unknown"


def set_model_warm(name: str, warm: bool = True) -> None:
    with _lock:
        _models_warm[name] = warm


def set_step_error(name: str, message: str) -> None:
    with _lock:
        _step_errors[name] = message


def set_search_mode(mode: str) -> None:
    global _search_mode
    _search_mode = mode


def get_search_mode() -> str:
    return _search_mode


def mark_bootstrap_complete() -> None:
    _bootstrap_complete.set()


def readiness() -> dict:
    with _lock:
        models_copy = dict(_models_warm)
        errors_copy = dict(_step_errors)
    return {
        "bootstrap_complete": _bootstrap_complete.is_set(),
        "models": models_copy,
        "all_warm": all(models_copy.values()),
        "bootstrap_step_errors": errors_copy,
        "search_mode": _search_mode,
    }
