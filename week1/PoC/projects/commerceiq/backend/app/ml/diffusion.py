"""Model 2 / 5 — Text-to-image generation.

segmind/tiny-sd: a knowledge-distilled, lightweight Stable Diffusion pipeline
(~530M params total across UNet/text-encoder/VAE), chosen specifically
because it runs on CPU in a reasonable time for a PoC (unlike full SD
1.5/XL). Runs inside a background job (see jobs.py) because CPU inference
takes tens of seconds.
"""
import os
import threading
import uuid

from ..config import settings

_lock = threading.Lock()
_pipe = None


def _load():
    global _pipe
    if _pipe is None:
        with _lock:
            if _pipe is None:
                import torch
                from diffusers import StableDiffusionPipeline

                _pipe = StableDiffusionPipeline.from_pretrained(
                    settings.diffusion_model,
                    torch_dtype=torch.float32,
                    safety_checker=None,
                )
                _pipe.set_progress_bar_config(disable=True)
    return _pipe


def generate_image(
    prompt: str,
    steps: int = 12,
    guidance_scale: float = 7.0,
    out_dir: str | None = None,
) -> str:
    pipe = _load()
    out_dir = out_dir or os.path.join(settings.data_dir, "generated")
    os.makedirs(out_dir, exist_ok=True)
    result = pipe(prompt, num_inference_steps=steps, guidance_scale=guidance_scale)
    image = result.images[0]
    filename = f"{uuid.uuid4().hex}.png"
    path = os.path.join(out_dir, filename)
    image.save(path)
    return path


def model_info() -> dict:
    pipe = _load()
    unet_params = sum(p.numel() for p in pipe.unet.parameters())
    text_encoder_params = sum(p.numel() for p in pipe.text_encoder.parameters())
    vae_params = sum(p.numel() for p in pipe.vae.parameters())
    return {
        "model_id": settings.diffusion_model,
        "unet_params": unet_params,
        "text_encoder_params": text_encoder_params,
        "vae_params": vae_params,
        "loaded": True,
    }
