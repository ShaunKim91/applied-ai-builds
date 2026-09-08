"""Model 1 / 5 — Vision classification.

WinKawaks/vit-tiny-patch16-224: a Vision Transformer distilled/trained small
enough to run comfortably on CPU (~5.7M params). Lazy-loaded singleton,
thread-safe.
"""
import threading

import torch
from PIL import Image
from transformers import ViTForImageClassification, ViTImageProcessor

from ..config import settings

_lock = threading.Lock()
_processor: ViTImageProcessor | None = None
_model: ViTForImageClassification | None = None


def _load():
    global _processor, _model
    if _model is None:
        with _lock:
            if _model is None:
                _processor = ViTImageProcessor.from_pretrained(settings.vit_model)
                _model = ViTForImageClassification.from_pretrained(settings.vit_model)
                _model.eval()
    return _processor, _model


def classify_image(image: Image.Image, top_k: int = 5) -> list[dict]:
    processor, model = _load()
    inputs = processor(images=image.convert("RGB"), return_tensors="pt")
    with torch.no_grad():
        outputs = model(**inputs)
    probs = torch.nn.functional.softmax(outputs.logits[0], dim=-1)
    values, indices = torch.topk(probs, min(top_k, probs.shape[-1]))
    return [
        {"label": model.config.id2label[i], "confidence": round(v, 4)}
        for v, i in zip(values.tolist(), indices.tolist())
    ]


def model_info() -> dict:
    _, model = _load()
    n_params = sum(p.numel() for p in model.parameters())
    return {"model_id": settings.vit_model, "params": n_params, "loaded": True}
