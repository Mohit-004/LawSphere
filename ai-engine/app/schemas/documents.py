"""Document ingestion and listing API contracts."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class TextDocumentRequest(BaseModel):
    title: str = Field(min_length=1, max_length=250)
    content: str = Field(min_length=1, max_length=2_000_000)
    source: str | None = Field(default=None, max_length=2000)

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("title must not be blank")
        return value


class DocumentSummary(BaseModel):
    id: str
    title: str
    source: str | None
    document_type: str
    chunk_count: int
    created_at: datetime


class DocumentIngestResponse(DocumentSummary):
    status: Literal["stored"]
    content_sha256: str


class DocumentListResponse(BaseModel):
    documents: list[DocumentSummary]


class DocumentIndexResponse(BaseModel):
    document_id: str
    embedding_model: str
    indexed_chunks: int
    vector_dimensions: int
    status: Literal["indexed"]


class SemanticSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=5, ge=1, le=20)

    @field_validator("query")
    @classmethod
    def query_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("query must not be blank")
        return value


class SearchResult(BaseModel):
    document_id: str
    chunk_id: int
    chunk_index: int
    title: str
    source: str | None = None
    document_type: str
    text: str
    start_offset: int
    end_offset: int
    page_number: int | None = None
    score: float


class SemanticSearchResponse(BaseModel):
    query: str
    embedding_model: str
    results: list[SearchResult]
