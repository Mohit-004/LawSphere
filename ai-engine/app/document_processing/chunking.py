"""Plain-text normalization and offset-preserving fixed-size chunking."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    text: str
    start_offset: int
    end_offset: int
    page_number: int | None = None


def normalize_text(text: str) -> str:
    """Normalize line endings and remove NUL bytes while preserving useful layout."""
    return text.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "").strip()


def chunk_text(
    text: str,
    max_chars: int = 1200,
    overlap: int = 160,
    page_ranges: list[tuple[int, int]] | None = None,
) -> list[TextChunk]:
    """Split text near paragraph or word boundaries and keep source offsets."""
    if max_chars <= 0:
        raise ValueError("max_chars must be greater than zero")
    if overlap < 0 or overlap >= max_chars:
        raise ValueError("overlap must be between zero and max_chars")

    has_page_metadata = page_ranges is not None
    if page_ranges is None:
        page_ranges = [(0, len(text))]

    chunks: list[TextChunk] = []
    for page_number, (range_start, range_end) in enumerate(page_ranges, start=1):
        chunks.extend(_chunk_range(
            text,
            range_start,
            range_end,
            max_chars,
            overlap,
            page_number if has_page_metadata else None,
        ))
    return chunks


def _chunk_range(
    text: str,
    range_start: int,
    range_end: int,
    max_chars: int,
    overlap: int,
    page_number: int | None,
) -> list[TextChunk]:
    chunks: list[TextChunk] = []
    start = range_start
    while start < range_end:
        end = min(start + max_chars, range_end)
        if end < range_end:
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
                page_number=page_number,
            ))

        if end >= range_end:
            break
        next_start = max(start + 1, end - overlap)
        while next_start < end and text[next_start].isspace():
            next_start += 1
        start = next_start
    return chunks
