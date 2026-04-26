import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.middleware.auth import get_current_user
from app.middleware.rate_limiter import rate_limiter
from app.rag.pdf_ingestion import MAX_PDF_SIZE_BYTES, ingest_pdf, list_uploaded_pdfs

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


class UploadResponse(BaseModel):
    message: str
    filename: str
    original_filename: str
    chunks_ingested: int
    pages_extracted: int


class DocumentInfo(BaseModel):
    filename: str
    chunk_count: int


class DocumentListResponse(BaseModel):
    documents: list[DocumentInfo]
    total: int


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_pdf(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Upload a PDF document to be indexed into the RAG knowledge base."""
    username = current_user["username"]

    # Rate limiting — shares the same limiter as /chat/
    allowed, remaining, _ = rate_limiter.is_allowed(username)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "limit": rate_limiter.max_requests,
                "window_seconds": rate_limiter.window_seconds,
                "retry_after": rate_limiter.window_seconds,
            },
        )

    # MIME type hint (Content-Type header — not authoritative, magic bytes check comes later)
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only PDF files are accepted",
        )

    # Early size rejection from Content-Length header (optional — may be absent)
    if file.size and file.size > MAX_PDF_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {MAX_PDF_SIZE_BYTES // (1024 * 1024)} MB",
        )

    content = await file.read()

    # Authoritative size check after reading full content
    if len(content) > MAX_PDF_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {MAX_PDF_SIZE_BYTES // (1024 * 1024)} MB",
        )

    try:
        result = ingest_pdf(content, file.filename or "upload.pdf")
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    logger.info(
        f"User '{username}' uploaded '{result['filename']}' "
        f"({result['chunks_ingested']} chunks)"
    )

    return UploadResponse(message="PDF uploaded and indexed successfully", **result)


@router.get("/", response_model=DocumentListResponse)
def list_documents(
    current_user: dict = Depends(get_current_user),
):
    """List all uploaded PDF documents in the knowledge base."""
    docs = list_uploaded_pdfs()
    return DocumentListResponse(
        documents=[DocumentInfo(**d) for d in docs],
        total=len(docs),
    )
