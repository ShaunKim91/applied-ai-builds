"""Model 3 / 6 — Speech-to-text (ASR).

openai-whisper, "tiny" checkpoint: a small, CPU-friendly model + size choice
for this kind of ASR task (37,184,640 params, encoder-decoder Transformer
with cross-attention). Requires the system `ffmpeg` binary to decode
arbitrary audio containers (installed in docker/Dockerfile) — Whisper
shells out to it internally, not a Python dependency.
"""
import threading

from ..config import settings

_lock = threading.Lock()
_model = None


def _load():
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                import whisper

                _model = whisper.load_model(settings.whisper_model)
    return _model


def transcribe(audio_path: str) -> dict:
    model = _load()
    result = model.transcribe(audio_path, fp16=False)
    return {
        "text": result.get("text", "").strip(),
        "language": result.get("language", ""),
    }


def model_info() -> dict:
    model = _load()
    n_params = sum(p.numel() for p in model.parameters())
    return {"model_id": f"whisper-{settings.whisper_model}", "params": n_params, "loaded": True}
