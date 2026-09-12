import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import Settings
from app.dependencies import get_app_settings, get_db
from services.document_service import (
    FileSizeLimitExceededError,
    SignalNotFoundError,
    get_document,
    save_and_process_document,
)
from services.text_extraction_service import (
    CorruptedFileError,
    UnsupportedFormatError,
)
from shared.schemas.document import DocumentUpload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post(
    "/upload",
    response_model=DocumentUpload,
    status_code=status.HTTP_201_CREATED,
    summary="Upload safety or regulatory document and extract text",
)
async def upload_document(
    file: UploadFile = File(...),
    signal_id: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_app_settings),
) -> DocumentUpload:
    """
    Accept regulatory/safety document (PDF, DOCX, TXT), validate format and size,
    extract text, and store metadata.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must have a filename.",
        )

    # Read content with size check
    try:
        content = await file.read()
    except Exception as exc:
        logger.error("Failed to read uploaded file: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read uploaded file data.",
        )

    try:
        result = save_and_process_document(
            filename=file.filename,
            content=content,
            content_type=file.content_type,
            signal_id=signal_id,
            db=db,
            settings=settings,
        )
        return result
    except FileSizeLimitExceededError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(exc),
        )
    except UnsupportedFormatError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except CorruptedFileError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except SignalNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except Exception as exc:
        logger.error("Document processing error: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the document.",
        )


@router.get(
    "/{document_id}",
    response_model=DocumentUpload,
    summary="Retrieve document metadata and extracted text preview",
)
def get_document_endpoint(
    document_id: str,
    db: Session = Depends(get_db),
) -> DocumentUpload:
    """Retrieve document metadata and extracted text preview by document_id."""
    doc = get_document(document_id, db)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found.",
        )
    return doc
