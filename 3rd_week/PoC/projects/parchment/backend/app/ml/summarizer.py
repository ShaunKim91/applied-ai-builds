"""Model 3 — a dedicated local abstractive-summarization transformer, used
for the PDF Summarizer tab.

sshleifer/distilbart-cnn-12-6: 306M-parameter distilled BART, fine-tuned on
CNN/DailyMail, Apache-2.0 licensed — verified to exist on the HuggingFace
Hub before being chosen here. This is a genuinely different local model
from llm.py's Qwen2.5-0.5B (a general instruction-following LLM); using a
model actually trained for summarization is a real upgrade over a naive
plain word-frequency rule-based summarizer, while staying 100% local and
key-free by default.

Long documents are chunked (`chunk_text`, the same word-count-with-overlap
technique used in the Week2 PoC) and summarized chunk-by-chunk, then the
per-chunk summaries are combined and summarized once more — the standard
"map-reduce" pattern for handling documents too long for a single pass.
"""
import re
import threading

from ..config import settings

_lock = threading.Lock()
_pipeline = None


def _load():
    global _pipeline
    if _pipeline is None:
        with _lock:
            if _pipeline is None:
                from transformers import pipeline

                _pipeline = pipeline("summarization", model=settings.summarizer_model)
    return _pipeline


def chunk_text(text: str, chunk_size: int | None = None, overlap: int | None = None) -> list[str]:
    """Splits `text` into ~chunk_size-word passages with `overlap` words
    shared between consecutive chunks, so content spanning a chunk boundary
    isn't lost. Same technique used in the Week2 PoC's fomc_minutes.py."""
    chunk_size = chunk_size or settings.pdf_chunk_size_words
    overlap = overlap or settings.pdf_chunk_overlap_words
    words = text.split()
    if not words:
        return []
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start = end - overlap
    return chunks


def _summarize_one(text: str, max_length: int = 120, min_length: int = 30) -> str:
    pipe = _load()
    word_count = len(text.split())
    # distilbart's max input is ~1024 tokens; truncation=True is required
    # (not optional) for the "reduce" step below, where the combined text
    # has no length guarantee — without it, BART's fixed position-embedding
    # limit raises an IndexError instead of just summarizing what fits.
    if word_count < 10:
        return text
    result = pipe(
        text,
        max_length=max_length,
        min_length=min(min_length, max(5, word_count // 4)),
        do_sample=False,
        truncation=True,
    )
    return result[0]["summary_text"].strip()


def _summarize_batch(texts: list[str], max_length: int = 100, min_length: int = 25, batch_size: int = 8) -> list[str]:
    """Batched summarization — one pipeline call over many chunks instead of
    one call per chunk. See debug/issue-01: a real 34,000-word PDF produced
    191 word-count chunks, and summarizing them one at a time sequentially
    took long enough to blow past a 180s HTTP timeout in this build's first
    real test. Batching gives the model's forward pass real parallelism
    across chunks instead of paying per-call Python/tokenization overhead
    191 times."""
    pipe = _load()
    results = pipe(texts, max_length=max_length, min_length=min_length, do_sample=False, truncation=True, batch_size=batch_size)
    return [r["summary_text"].strip() for r in results]


# Hard cap on how many chunks get individually summarized for one document.
# Without this, a long enough PDF (a few hundred pages) could still take
# several minutes even batched — a real 34,000-word PDF with a 60-chunk cap
# still measured ~167s end to end in this build's own testing, uncomfortably
# close to a 180s timeout. Chunks beyond the cap are evenly dropped (not
# just truncated from the end) so the summary still reflects the whole
# document's span rather than only its opening section — and the caller is
# told exactly how many were skipped rather than this happening silently.
MAX_CHUNKS = 20


def summarize_long_text(text: str) -> dict:
    """Map-reduce summarization for arbitrarily long text."""
    chunks = chunk_text(text)
    if not chunks:
        return {"summary": "", "chunk_count": 0, "chunks_summarized": 0}
    if len(chunks) == 1:
        return {"summary": _summarize_one(chunks[0]), "chunk_count": 1, "chunks_summarized": 1}

    if len(chunks) > MAX_CHUNKS:
        # Evenly sample MAX_CHUNKS indices across the full document span.
        step = len(chunks) / MAX_CHUNKS
        sampled = [chunks[int(i * step)] for i in range(MAX_CHUNKS)]
    else:
        sampled = chunks

    partial_summaries = _summarize_batch(sampled)
    combined = " ".join(partial_summaries)
    final = _summarize_one(combined, max_length=160, min_length=40)
    return {"summary": final, "chunk_count": len(chunks), "chunks_summarized": len(sampled)}


_NUMBER_RE = re.compile(r"\d[\d,]*\.?\d*%?")


def _appears_in(number: str, source_text: str) -> bool:
    """Checks whether `number` (e.g. "2%" or "5.5") appears in `source_text`
    — trying both the literal form AND, for a "%"-suffixed number, its
    spelled-out "N percent" / "N per cent" equivalent. A real Fed report
    summarized by OpenRouter's qwen3-8b stated "2% inflation target," which
    is a true fact directly from the source — the source just spells it
    "2 percent" rather than using the % symbol. Without this normalization,
    numeric_cross_check flags a real, verifiable number as "unverified"
    purely because of a notation difference, not because it's wrong."""
    if number in source_text:
        return True
    if number.endswith("%"):
        digits = number[:-1]
        return bool(re.search(rf"{re.escape(digits)}\s*per\s*cent", source_text, re.IGNORECASE))
    return False


def numeric_cross_check(summary: str, source_text: str) -> dict:
    """The "a summary is a reference, numbers must come from the source"
    discipline made concrete: every distinct number the summary states
    must appear (literally, or as a verified "N percent" equivalent —
    see `_appears_in`) somewhere in the source text."""
    summary_numbers = set(_NUMBER_RE.findall(summary))
    if not summary_numbers:
        return {"passed": True, "checked": 0, "unverified": []}
    unverified = [n for n in summary_numbers if not _appears_in(n, source_text)]
    return {"passed": len(unverified) == 0, "checked": len(summary_numbers), "unverified": unverified}


def model_info() -> dict:
    _load()
    return {"model_id": settings.summarizer_model, "loaded": True}
