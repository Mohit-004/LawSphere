"""Plain-text normalization and offset-preserving fixed-size chunking."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    text: str
    start_offset: int
    end_offset: int


def normalize_text(text: str) -> str:
    """Normalize line endings and remove NUL bytes while preserving useful layout."""
    return text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "").strip()


def chunk_text(text: str, max_chars: int = 1200, overlap: int = 160) -> list[TextChunk]:
    """Split text near paragraph or word boundaries and keep source offsets."""
    if max_chars <= 0:
        raise ValueError("max_chars must be greater than zero")
    if overlap < 0 or overlap >= max_chars:
        raise ValueError("overlap must be between zero and max_chars")

    chunks: list[TextChunk] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            search_start = start + max_chars // 2
            boundaries = (
                (text.rfind("\n\n", search_start, end), 2),
                (text.rfind("\n", search_start, end), 1),
                (text.rfind(" ", search_start, end), 1),
            )
            boundary, delimiter_size = max(boundaries, key=lambda item: item[0])
            if boundary > start:
                end = boundary + delimiter_size

        raw_text = text[start:end]
        leading = len(raw_text) - len(raw_text.lstrip())
        trailing = len(raw_text) - len(raw_text.rstrip())
        content_start = start + leading
        content_end = end - trailing
        if content_start < content_end:
            chunks.append(TextChunk(
                text=text[content_start:content_end],
                start_offset=content_start,
                end_offset=content_end,
            ))

        if end >= len(text):
            break
        next_start = max(start + 1, end - overlap)
        while next_start < end and text[next_start].isspace():
            next_start += 1
        start = next_start

    return chunks
