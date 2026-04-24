"""
Text chunker with overlap.
Splits text into overlapping chunks for better retrieval context.
"""
from typing import List
from src.config import CHUNK_SIZE, CHUNK_OVERLAP


def chunk_text(text: str, file_path: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[dict]:
    """
    Split text into overlapping chunks.
    Returns list of chunk dicts with text, index, and metadata.
    """
    if not text or not text.strip():
        return []

    # Clean text
    text = text.strip()
    chunks = []
    start = 0
    chunk_index = 0

    while start < len(text):
        end = start + chunk_size

        # Try to break at a sentence boundary
        if end < len(text):
            # Look back up to 100 chars for a good break point
            break_point = _find_break(text, end, lookback=100)
            end = break_point

        chunk_text_content = text[start:end].strip()

        if chunk_text_content:
            chunks.append({
                "text": chunk_text_content,
                "chunk_index": chunk_index,
                "start_char": start,
                "end_char": end,
                "file_path": file_path,
            })
            chunk_index += 1

        # Move forward with overlap
        start = end - overlap
        if start <= 0:
            break

    return chunks


def _find_break(text: str, pos: int, lookback: int = 100) -> int:
    """Find the nearest sentence/paragraph break before pos."""
    search_from = max(0, pos - lookback)
    segment = text[search_from:pos]

    # Prefer paragraph break
    idx = segment.rfind("\n\n")
    if idx != -1:
        return search_from + idx + 2

    # Then newline
    idx = segment.rfind("\n")
    if idx != -1:
        return search_from + idx + 1

    # Then sentence end
    for punct in (". ", "! ", "? "):
        idx = segment.rfind(punct)
        if idx != -1:
            return search_from + idx + len(punct)

    return pos
