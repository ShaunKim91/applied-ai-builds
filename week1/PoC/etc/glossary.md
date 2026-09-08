# Glossary & Model Cards — CommerceIQ

## AI models used

### 1. WinKawaks/vit-tiny-patch16-224 (Vision Transformer)
- **What it is**: a small Vision Transformer (ViT), pretrained on ImageNet-1k, ~5.7M parameters.
- **Why chosen**: a well-established, CPU-friendly classification model; small enough to load in well under a second on a laptop CPU.
- **How CommerceIQ uses it**: Catalog Vision tab — classifies uploaded/sample product photos into ImageNet's 1,000 classes, shown as a top-5 ranked list with confidence scores.
- **Card**: <https://huggingface.co/WinKawaks/vit-tiny-patch16-224>
- **Background reading**: Dosovitskiy, A. et al. "An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale." *ICLR 2021*. <https://arxiv.org/abs/2010.11929>

### 2. segmind/tiny-sd (distilled Stable Diffusion)
- **What it is**: a knowledge-distilled, lightweight Stable Diffusion pipeline (~530M params across U-Net/text-encoder/VAE combined) — roughly half the size of standard SD 1.5.
- **Why chosen**: same reasoning as above — a CPU-friendly choice, and one of the few diffusion pipelines that completes an image in a reasonable time on CPU-only hardware.
- **How CommerceIQ uses it**: Generative Studio tab — text prompt to product/marketing image, with adjustable steps and guidance scale, run as a background job.
- **Card**: <https://huggingface.co/segmind/tiny-sd>
- **Background reading**: Rombach, R. et al. "High-Resolution Image Synthesis with Latent Diffusion Models." *CVPR 2022*. <https://arxiv.org/abs/2112.10752> (Stable Diffusion's underlying architecture); Sohl-Dickstein, J. et al. "Deep Unsupervised Learning using Nonequilibrium Thermodynamics." *ICML 2015*. <https://arxiv.org/abs/1503.03585> (diffusion models' origin)

### 3. intfloat/multilingual-e5-small
- **What it is**: a 384-dimension multilingual sentence-embedding model (E5 family), strong on both English and Korean retrieval tasks.
- **Why chosen**: a standard choice for multilingual RAG, validated here with measured before/after retrieval-quality comparisons against alternatives, as the project brief encourages.
- **How CommerceIQ uses it**: embeds classified-catalog-item descriptions for the Semantic Search feature; uses the E5 convention of `"query: "` / `"passage: "` text prefixes for asymmetric retrieval.
- **Card**: <https://huggingface.co/intfloat/multilingual-e5-small>
- **Background reading**: Wang, L. et al. "Text Embeddings by Weakly-Supervised Contrastive Pre-training." 2022. <https://arxiv.org/abs/2212.03533>

### 4. Qwen/Qwen2.5-0.5B-Instruct (local narrative LLM)
- **What it is**: a 0.5B-parameter instruction-tuned open-weight LLM from Alibaba's Qwen team.
- **Why chosen**: a go-to small local LLM for fully offline, no-API-key text generation.
- **How CommerceIQ uses it**: default (no-key) provider for the Demand Forecasting "AI insight" narrative.
- **Card**: <https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct>

### 5. qwen/qwen3-8b via OpenRouter (optional cloud upgrade)
- **What it is**: an 8B-parameter Qwen3 model, served via OpenRouter's hosted API.
- **Why chosen**: cheap ($0.117 / $0.455 per million input/output tokens as of Aug 2026 — verified live against openrouter.ai during this build, not assumed from training memory), and the project brief specifically asked for an OpenRouter-validated cloud path this round.
- **How CommerceIQ uses it**: strictly opt-in (a checkbox in the Forecasting UI) alternative to the local LLM for the same "AI insight" feature — same prompt, different backend, so the quality difference is directly comparable.
- **Card**: <https://openrouter.ai/qwen/qwen3-8b>

## Key terms

| Term | Meaning in this project |
|---|---|
| **PoC** | Proof of Concept — a project built to demonstrate feasibility and depth of an idea at a professional-leaning quality bar, distinct from both a toy demo and a shipped product. |
| **Hybrid architecture** | A recurring pattern used consistently across this project series: a local, no-key, always-working default, with cloud APIs as strictly optional, independently-failing upgrades. CommerceIQ's `ml/llm.py` follows the same pattern. |
| **Lazy-loaded singleton** | A model is only loaded into memory the first time it's actually needed (not at process startup), and reused after that — keeps a cold start fast and avoids loading models nobody ends up using this run. |
| **Audit trail** | The `audit_logs` SQL table — every AI inference call is recorded with who made it, which model, how long it took, and whether it succeeded, mirroring the standard "감사 추적" (audit trail) concept common to agentic-AI system design. |
| **Backtest (forecasting)** | Refitting a model on all-but-the-last-N days and scoring its forecast of those N days against what actually happened — the only valid way to estimate a time-series model's real-world error (never a random train/test split, which leaks future information into the past). |
| **CI band (confidence interval)** | The shaded region around the forecast line showing the range the true value is expected to fall within (95%, i.e. ±1.96 standard deviations of the model's residuals). |
