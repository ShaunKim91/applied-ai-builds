"""Bootstrap/readiness state — the same `_warm_step()` isolation pattern
validated across every prior PoC in this project series."""
import threading

_lock = threading.Lock()
_models_warm: dict[str, bool] = {"embeddings": False, "local_agent": False}
_bootstrap_complete = threading.Event()
_step_errors: dict[str, str] = {}


def set_model_warm(name: str, warm: bool = True) -> None:
    with _lock:
        _models_warm[name] = warm


def set_step_error(name: str, message: str) -> None:
    with _lock:
        _step_errors[name] = message


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
    }
