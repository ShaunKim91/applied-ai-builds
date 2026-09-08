# Issue 01 — `setup.sh` reported the wrong local model count

## Symptom

The first real `./scripts/setup.sh` run for VoxIQ completed and started the
container successfully, but printed a misleading status message:

```
Waiting for the API to respond (public datasets + all 4 local AI models
download/warm up in the background on first boot — this can take a few minutes)...
```

VoxIQ actually loads **5** local models (bi-encoder, cross-encoder, Whisper,
the local Qwen2.5-0.5B-Instruct LLM, and GPT-2 for the tokenizer/attention
explorer) — `download_models.sh` and `README.md` both correctly say "5" in
the same project.

## Root cause

`scripts/setup.sh` was adapted from the Week1 PoC's ("CommerceIQ")
equivalent script, which has exactly 4 local models. The count in this one
status echo line was never updated when the script was carried over to
VoxIQ's 5-model lineup — a plain leftover from copy-adapting a working
template rather than a logic bug.

## Fix applied

Changed the string in `scripts/setup.sh` from "all 4 local AI models" to
"all 5 local AI models" to match `download_models.sh`, `README.md`, and the
actual bootstrap sequence in `backend/app/main.py`.

## Verification

Re-read `scripts/setup.sh`, `scripts/download_models.sh`, and `README.md`
side-by-side after the fix — all three now consistently say "5".

## What to study if this is new to you

- **Reused templates carry their old assumptions with them.** Copying a
  proven script (Week1's `setup.sh`) is the right move for saving time, but
  every literal value baked into its output strings (counts, names, ports)
  needs a deliberate re-check against the new project's actual numbers — the
  script still runs fine either way, so nothing *fails*; it just quietly
  tells the operator something false.
