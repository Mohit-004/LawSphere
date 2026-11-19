"""Local plain-text document ingestion endpoints."""

import hashlib
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database.models import Document, DocumentChunk
from app.database.session import get_database_session
from app.document_processing.chunking import chunk_text, normalize_text
from app.schemas.documents import (
    DocumentIngestResponse,
    DocumentListResponse,
    DocumentSummary,
    TextDocumentRequest,
)

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


@router.post("/text", response_model=DocumentIngestResponse, status_code=status.HTTP_201_CREATED)
def ingest_text_document(
    request: TextDocumentRequest,
    session: Session = Depends(get_database_session),
) -> DocumentIngestResponse:
    """Store a text source and create chunks with offsets into its normalized content."""
    content = normalize_text(request.content)
    if not content:
        raise HTTPException(status_code=422, detail="Document content must not be blank.")

    segments = chunk_text(content)
    document_id = str(uuid4())
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    document = Document(
        id=document_id,
        title=request.title,
        source=request.source,
        content=content,
        content_sha256=digest,
    )
    document.chunks = [
        DocumentChunk(
            chunk_index=index,
            text=segment.text,
            start_offset=segment.start_offset,
            end_offset=segment.end_offset,
        )
        for index, segment in enumerate(segments)
    ]

    try:
        session.add(document)
        session.commit()
        session.refresh(document)
    except SQLAlchemyError as exception:
        session.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not store this document in the local database.",
        ) from exception

    return DocumentIngestResponse(
        id=document.id,
        title=document.title,
        source=document.source,
        chunk_count=len(document.chunks),
        created_at=document.created_at,
        status="stored",
        content_sha256=document.content_sha256,
    )


@router.get("", response_model=DocumentListResponse)
def list_documents(
    limit: int = Query(default=50, ge=1, le=100),
    session: Session = Depends(get_database_session),
) -> DocumentListResponse:
    """List recently stored local text sources."""
    documents = session.scalars(
        select(Document).order_by(Document.created_at.desc()).limit(limit)
    ).all()
    return DocumentListResponse(
        documents=[
            DocumentSummary(
                id=document.id,
                title=document.title,
                source=document.source,
                chunk_count=len(document.chunks),
                created_at=document.created_at,
            )
            for document in documents
        ]
    )
