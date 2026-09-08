"""Model 6 / 6 — Tokenizer & Attention Explorer (bonus feature).

GPT-2 (117M): used here purely to make core Transformer concepts
("tokenization isn't word-splitting" and "self-attention connects every
token to every other token") tangible and inspectable, rather than to power
a product feature. Same tokenizer family commonly used to illustrate Korean
vs English token-count inefficiency.
"""
import threading

from ..config import settings

_lock = threading.Lock()
_tokenizer = None
_model = None

MAX_TOKENS_FOR_ATTENTION = 40  # keeps the attention heatmap readable + fast


def _load():
    global _tokenizer, _model
    if _model is None:
        with _lock:
            if _model is None:
                from transformers import GPT2LMHeadModel, GPT2Tokenizer

                _tokenizer = GPT2Tokenizer.from_pretrained(settings.tokenizer_model)
                _model = GPT2LMHeadModel.from_pretrained(settings.tokenizer_model, output_attentions=True)
                _model.eval()
    return _tokenizer, _model


def tokenize(text: str) -> dict:
    tokenizer, _ = _load()
    ids = tokenizer.encode(text)
    tokens = [tokenizer.decode([i]) for i in ids]
    return {"tokens": tokens, "ids": ids, "count": len(ids)}


def attention_weights(text: str, layer: int | None = None) -> dict:
    import torch

    tokenizer, model = _load()
    inputs = tokenizer(text, return_tensors="pt")
    if inputs["input_ids"].shape[1] > MAX_TOKENS_FOR_ATTENTION:
        inputs["input_ids"] = inputs["input_ids"][:, :MAX_TOKENS_FOR_ATTENTION]
        inputs["attention_mask"] = inputs["attention_mask"][:, :MAX_TOKENS_FOR_ATTENTION]

    with torch.no_grad():
        outputs = model(**inputs)

    # outputs.attentions: tuple of `n_layers` tensors, each (batch, heads, seq, seq)
    n_layers = len(outputs.attentions)
    chosen_layer = n_layers - 1 if layer is None else max(0, min(layer, n_layers - 1))
    layer_attn = outputs.attentions[chosen_layer][0]  # (heads, seq, seq)
    avg_attn = layer_attn.mean(dim=0)  # average across heads -> (seq, seq)

    tokens = [tokenizer.decode([i]) for i in inputs["input_ids"][0].tolist()]
    return {
        "tokens": tokens,
        "attention": [[round(v, 4) for v in row] for row in avg_attn.tolist()],
        "layer": chosen_layer,
        "num_layers": n_layers,
        "truncated": len(tokenizer.encode(text)) > MAX_TOKENS_FOR_ATTENTION,
    }


def model_info() -> dict:
    _, model = _load()
    n_params = sum(p.numel() for p in model.parameters())
    return {"model_id": settings.tokenizer_model, "params": n_params, "loaded": True}
