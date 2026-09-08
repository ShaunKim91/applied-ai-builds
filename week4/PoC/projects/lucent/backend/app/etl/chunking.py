"""Word-overlap chunking — the same technique validated in the Week2/3
PoCs, and a real improvement over a naive chunker that slices by raw
character count with **no overlap** at all (overlap is often discussed
only as a conceptual code sample in introductory material, never actually
wired into the shipped chunker). Losing content that straddles a cut point
is exactly the failure mode overlap exists to prevent — worth actually
implementing here, not just explaining.
"""
from ..config import settings


def chunk_text(text: str, chunk_size: int | None = None, overlap: int | None = None) -> list[str]:
    chunk_size = chunk_size or settings.chunk_size_words
    overlap = overlap or settings.chunk_overlap_words
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
