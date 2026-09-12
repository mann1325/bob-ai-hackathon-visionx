import logging
import os
import uuid
from typing import List, Optional
from sqlalchemy.orm import Session

from app.config import Settings
from database.models import DocumentUploadModel, SignalModel
from services.text_extraction_service import (
    CorruptedFileError,
    UnsupportedFormatError,
    extract_text,
)
from shared.schemas.document import DocumentUpload

logger = logging.getLogger(__name__)


class FileSizeLimitExceededError(Exception):
    """Raised when the uploaded file exceeds the configured size limit."""
    pass


class SignalNotFoundError(Exception):
    """Raised when the associated signal_id does not exist."""
    pass


def save_and_process_document(
    filename: str,
    content: bytes,
    content_type: Optional[str] = None,
    signal_id: Optional[str] = None,
    db: Optional[Session] = None,
    settings: Optional[Settings] = None,
) -> DocumentUpload:
    """
    Validate, store, extract text, and persist an uploaded regulatory/safety document.
    """
    if not filename:
        filename = "unnamed_document"

    safe_filename = os.path.basename(filename)
    file_size = len(content)

    max_size = (
        settings.max_upload_size_bytes
        if settings
        else 10 * 1024 * 1024
    )
    if file_size > max_size:
        raise FileSizeLimitExceededError(
            f"File size {file_size} bytes exceeds maximum allowed limit of {max_size} bytes."
        )

    # Validate signal_id if provided and database is available
    if signal_id and db is not None:
        signal_exists = db.query(SignalModel).filter(SignalModel.signal_id == signal_id).first()
        # If signals table has entries but this specific signal does not exist, raise SignalNotFoundError
        total_signals = db.query(SignalModel).count()
        if total_signals > 0 and signal_exists is None:
            raise SignalNotFoundError(f"Referenced signal '{signal_id}' was not found.")

    # Extract text and validate file format/signature
    file_type, extracted_text = extract_text(safe_filename, content, content_type)

    # Generate secure document ID
    document_id = f"doc_{uuid.uuid4().hex[:12]}"

    # Save file to configured storage directory
    upload_dir = settings.upload_dir if settings else "data/uploads"
    os.makedirs(upload_dir, exist_ok=True)
    storage_path = os.path.join(upload_dir, f"{document_id}.bin")

    try:
        with open(storage_path, "wb") as f:
            f.write(content)
    except Exception as exc:
        logger.error("Failed to write document file to storage: %s", type(exc).__name__)
        raise

    preview = (
        extracted_text[:500]
        if extracted_text
        else ""
    )

    doc_record = DocumentUploadModel(
        document_id=document_id,
        filename=safe_filename,
        file_type=file_type,
        file_size_bytes=file_size,
        signal_id=signal_id,
        extracted_text=extracted_text,
        extracted_text_preview=preview,
        status="extracted",
        storage_path=storage_path,
    )

    if db is not None:
        db.add(doc_record)
        db.commit()
        db.refresh(doc_record)
        uploaded_at = doc_record.created_at
    else:
        uploaded_at = None

    return DocumentUpload(
        document_id=document_id,
        filename=safe_filename,
        file_type=file_type,
        file_size_bytes=file_size,
        signal_id=signal_id,
        uploaded_at=uploaded_at,
        extracted_text_preview=preview,
        status=doc_record.status,
    )


def get_document(document_id: str, db: Session) -> Optional[DocumentUpload]:
    """Retrieve document metadata and preview by document_id."""
    doc = db.query(DocumentUploadModel).filter(DocumentUploadModel.document_id == document_id).first()
    if not doc:
        return None

    return DocumentUpload(
        document_id=doc.document_id,
        filename=doc.filename,
        file_type=doc.file_type,
        file_size_bytes=doc.file_size_bytes,
        signal_id=doc.signal_id,
        uploaded_at=doc.created_at,
        extracted_text_preview=doc.extracted_text_preview,
        status=doc.status,
    )


def get_document_model(document_id: str, db: Session) -> Optional[DocumentUploadModel]:
    """Retrieve raw DocumentUploadModel by document_id."""
    return db.query(DocumentUploadModel).filter(DocumentUploadModel.document_id == document_id).first()


def list_documents_for_signal(signal_id: str, db: Session) -> List[DocumentUpload]:
    """Retrieve all documents associated with a signal."""
    docs = db.query(DocumentUploadModel).filter(DocumentUploadModel.signal_id == signal_id).all()
    return [
        DocumentUpload(
            document_id=doc.document_id,
            filename=doc.filename,
            file_type=doc.file_type,
            file_size_bytes=doc.file_size_bytes,
            signal_id=doc.signal_id,
            uploaded_at=doc.created_at,
            extracted_text_preview=doc.extracted_text_preview,
            status=doc.status,
        )
        for doc in docs
    ]
