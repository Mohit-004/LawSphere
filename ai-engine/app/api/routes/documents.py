"""Local plain-text document ingestion endpoints."""

import hashlib
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.models import Document, DocumentChunk
from app.database.session import get_database_session
from app.document_processing.chunking import chunk_text, normalize_text
from app.document_processing.extractors import (
    DocumentExtractionError,
    extract_docx,
    extract_pdf,
)
from app.embeddings.ollama import EmbeddingError, OllamaEmbeddingProvider
from app.vector_store.qdrant import VectorStoreError, index_document_chunks
from app.schemas.documents import (
    DocumentIndexResponse,
    DocumentIngestResponse,
    DocumentListResponse,
    DocumentSummary,
    TextDocumentRequest,
)

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_EXTRACTED_TEXT_CHARS = 2_000_000


def _store_document(
    session: Session,
    *,
    title: str,
    source: str | None,
    content: str,
    document_type: str,
    stored_path: Path | None = None,
    page_ranges: list[tuple[int, int]] | None = None,
) -> DocumentIngestResponse:
    segments = chunk_text(content, page_ranges=page_ranges)
    document_id = str(uuid4())
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    document = Document(
        id=document_id,
        title=title,
        source=source,
        document_type=document_type,
        stored_path=str(stored_path) if stored_path else None,
        content=content,
        content_sha256=digest,
    )
    document.chunks = [
        DocumentChunk(
            chunk_index=index,
            text=segment.text,
            start_offset=segment.start_offset,
            end_offset=segment.end_offset,
            page_number=segment.page_number,
        )
        for index, segment in enumerate(segments)
    ]

    try:
        session.add(document)
        session.commit()
        session.refresh(document)
    except SQLAlchemyError as exception:
        session.rollback()
        if stored_path is not None:
            stored_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=500,
            detail="Could not store this document in the local database.",
        ) from exception

    return DocumentIngestResponse(
        id=document.id,
        title=document.title,
        source=document.source,
        document_type=document.document_type,
        chunk_count=len(document.chunks),
        created_at=document.created_at,
        status="stored",
        content_sha256=document.content_sha256,
    )


@router.post("/text", response_model=DocumentIngestResponse, status_code=status.HTTP_201_CREATED)
def ingest_text_document(
    request: TextDocumentRequest,
    session: Session = Depends(get_database_session),
) -> DocumentIngestResponse:
    """Store a text source and create chunks with offsets into its normalized content."""
    content = normalize_text(request.content)
    if not content:
        raise HTTPException(status_code=422, detail="Document content must not be blank.")

    return _store_document(
        session,
        title=request.title,
        source=request.source,
        content=content,
        document_type="text",
    )


@router.post("/upload", response_model=DocumentIngestResponse, status_code=status.HTTP_201_CREATED)
def upload_document(
    file: UploadFile = File(...),
    title: str | None = Form(default=None, max_length=250),
    source: str | None = Form(default=None, max_length=2000),
    session: Session = Depends(get_database_session),
) -> DocumentIngestResponse:
    """Extract and store text from a PDF or DOCX while keeping the original locally."""
    filename = Path(file.filename or "document").name
    extension = Path(filename).suffix.lower()
    if extension not in {".pdf", ".docx"}:
        raise HTTPException(status_code=415, detail="Only PDF and DOCX files are supported.")

    data = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Uploads are limited to 20 MB.")
    if not data:
        raise HTTPException(status_code=422, detail="The uploaded file is empty.")

    try:
        if extension == ".pdf":
            extracted = extract_pdf(data)
        else:
            extracted = extract_docx(data)
    except DocumentExtractionError as exception:
        raise HTTPException(status_code=422, detail=str(exception)) from exception
    if len(extracted.text) > MAX_EXTRACTED_TEXT_CHARS:
        raise HTTPException(
            status_code=413,
            detail="Extracted text exceeds the 2 million character processing limit.",
        )

    document_title = (title or Path(filename).stem).strip()
    if not document_title:
        document_title = "Imported document"
    if len(document_title) > 250:
        raise HTTPException(status_code=422, detail="Document titles are limited to 250 characters.")
    document_type = extension[1:]

    storage_directory = settings.database_path.parent.parent / "documents"
    storage_directory.mkdir(parents=True, exist_ok=True)
    stored_path = storage_directory / f"{uuid4().hex}{extension}"
    temporary_path = stored_path.with_name(stored_path.name + ".tmp")
    temporary_path.write_bytes(data)
    temporary_path.replace(stored_path)

    return _store_document(
        session,
        title=document_title,
        source=source,
        content=extracted.text,
        document_type=document_type,
        stored_path=stored_path,
        page_ranges=extracted.page_ranges,
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
                document_type=document.document_type,
                chunk_count=len(document.chunks),
                created_at=document.created_at,
            )
            for document in documents
        ]
    )


@router.post("/{document_id}/index", response_model=DocumentIndexResponse)
def index_document(
    document_id: str,
    session: Session = Depends(get_database_session),
) -> DocumentIndexResponse:
    """Embed stored chunks with Ollama and persist them in local Qdrant."""
    document = session.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document was not found.")
    chunks = list(session.scalars(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
    ).all())
    if not chunks:
        raise HTTPException(status_code=422, detail="Document has no chunks to index.")

    try:
        embeddings = OllamaEmbeddingProvider().embed_texts([chunk.text for chunk in chunks])
        index_document_chunks(document, chunks, embeddings)
    except EmbeddingError as exception:
        raise HTTPException(status_code=503, detail=str(exception)) from exception
    except VectorStoreError as exception:
        raise HTTPException(status_code=500, detail=str(exception)) from exception

    return DocumentIndexResponse(
        document_id=document.id,
        embedding_model=settings.embedding_model,
        indexed_chunks=len(chunks),
        vector_dimensions=len(embeddings[0]),
        status="indexed",
    )
