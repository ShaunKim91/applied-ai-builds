"""Model 2 — a real local vision-language model (SmolVLM-256M-Instruct).

This is the "pretrained multimodal AI" side of the comparison this tab
draws, running with zero API key: the model reads the image's pixels
directly and answers a question about it, with no separate OCR step.
Contrast with ocr.py, which extracts raw text first and structures it
afterward — the Receipts tab runs both on the same image and shows both
results, so the underlying concept ("don't train your own CNN — use a
pretrained multimodal model") is directly visible rather than only
narrated.

HuggingFaceTB/SmolVLM-256M-Instruct: 256M parameters (a 93M vision encoder +
the 135M SmolLM2 language model), documented as "the smallest multimodal
model in the world," explicitly designed for on-device/CPU-feasible
inference — verified via its HuggingFace model card before being chosen
here.
"""
import threading

from ..config import settings

_lock = threading.Lock()
_model = None
_processor = None


def _load():
    global _model, _processor
    if _model is None:
        with _lock:
            if _model is None:
                from transformers import AutoModelForVision2Seq, AutoProcessor

                _processor = AutoProcessor.from_pretrained(settings.vlm_model)
                _model = AutoModelForVision2Seq.from_pretrained(settings.vlm_model)
                _model.eval()
    return _processor, _model


def ask_image(image_path: str, question: str, max_new_tokens: int = 200) -> str:
    from PIL import Image

    processor, model = _load()
    with Image.open(image_path) as img:
        image = img.convert("RGB")
        messages = [
            {
                "role": "user",
                "content": [{"type": "image"}, {"type": "text", "text": question}],
            }
        ]
        prompt = processor.apply_chat_template(messages, add_generation_prompt=True)
        inputs = processor(text=prompt, images=[image], return_tensors="pt")
        generated_ids = model.generate(**inputs, max_new_tokens=max_new_tokens)
        output = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
    # The decoded output repeats the prompt template before the answer;
    # keep only what follows the model's own "Assistant:" turn marker.
    if "Assistant:" in output:
        output = output.split("Assistant:", 1)[1]
    return output.strip()


def model_info() -> dict:
    _, model = _load()
    n_params = sum(p.numel() for p in model.parameters())
    return {"model_id": settings.vlm_model, "params": n_params, "loaded": True}
