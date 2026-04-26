import io
import logging
import os
import re

import pypdf
import pypdf.errors

from app.rag.vectorstore import _chunk_text, get_collection
from app.security.content_moderation import moderate_input

logger = logging.getLogger(__name__)

MAX_PDF_SIZE_BYTES = 10 * 1024 * 1024
PDF_MAGIC_BYTES = b"%PDF"
MAX_MODERATION_EXCERPT_CHARS = 5_000
UPLOAD_CHUNK_SIZE = 500
UPLOAD_CHUNK_OVERLAP = 50


def validate_pdf_magic_bytes(header: bytes) -> None:
    if header[:4] != PDF_MAGIC_BYTES:
        raise ValueError("Not a valid PDF file")


def sanitize_filename(original_name: str) -> str:
    base = os.path.basename(original_name.strip())
    stem, _, _ = base.rpartition(".")
    if not stem:
        stem = base

    stem = re.sub(r"[^\w\-]", "_", stem)
    stem = re.sub(r"_+", "_", stem).strip("_")

    if not stem:
        stem = "upload"

    return f"{stem}.pdf"


def extract_text_from_pdf(content: bytes) -> str:
    try:
        reader = pypdf.PdfReader(io.BytesIO(content))
        pages = [page.extract_text() or "" for page in reader.pages]
        text = "\n\n".join(pages)
    except pypdf.errors.PdfReadError as e:
        raise ValueError(f"PDF is encrypted or malformed: {e}")

    if not text.strip():
        raise ValueError(
            "PDF contains no extractable text (may be a scanned image — OCR not supported)"
        )

    return text


def check_content_safety(text: str) -> None:
    excerpt = text[:MAX_MODERATION_EXCERPT_CHARS]
    is_safe, _, violations = moderate_input(excerpt)
    if not is_safe:
        raise ValueError(f"PDF content flagged by moderation: {', '.join(violations)}")


def ingest_pdf(content: bytes, original_filename: str) -> dict:
    if len(content) > MAX_PDF_SIZE_BYTES:
        raise ValueError(
            f"PDF exceeds maximum allowed size of {MAX_PDF_SIZE_BYTES // (1024 * 1024)} MB"
        )

    validate_pdf_magic_bytes(content[:4])

    safe_filename = sanitize_filename(original_filename)
    stem = safe_filename[:-4]

    text = extract_text_from_pdf(content)

    check_content_safety(text)

    chunks = _chunk_text(text, chunk_size=UPLOAD_CHUNK_SIZE, overlap=UPLOAD_CHUNK_OVERLAP)

    ids = [f"pdf_{stem}_chunk_{i}" for i in range(len(chunks))]
    metadatas = [
        {"source": safe_filename, "chunk_index": i, "upload": True}
        for i in range(len(chunks))
    ]

    collection = get_collection()
    collection.upsert(ids=ids, documents=chunks, metadatas=metadatas)

    page_count = text.count("\n\n") + 1

    logger.info(
        f"Ingested PDF '{safe_filename}': {len(chunks)} chunks from ~{page_count} pages"
    )

    return {
        "filename": safe_filename,
        "original_filename": original_filename,
        "chunks_ingested": len(chunks),
        "pages_extracted": page_count,
    }


def list_uploaded_pdfs() -> list[dict]:
    collection = get_collection()
    result = collection.get(where={"upload": True}, include=["metadatas"])

    seen: dict[str, int] = {}
    for meta in result["metadatas"]:
        fname = meta["source"]
        seen[fname] = seen.get(fname, 0) + 1

    return [{"filename": fname, "chunk_count": count} for fname, count in seen.items()]
