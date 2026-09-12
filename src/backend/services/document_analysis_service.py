import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from ai.gemini_client import (
    DEFAULT_GEMINI_MODEL,
    GeminiAPIError,
    GeminiAuthError,
    GeminiClient,
)
from app.config import Settings, get_settings
from database.models import DocumentAnalysisModel, DocumentUploadModel, SignalModel
from shared.schemas.ai import GeminiAnalysis, RelevantSection

logger = logging.getLogger(__name__)


def get_signal_context(db: Session, signal_id: Optional[str]) -> Optional[Dict[str, Any]]:
    """Retrieve signal facts if signal_id is present and exists."""
    if not signal_id:
        return None

    signal = db.query(SignalModel).filter(SignalModel.signal_id == signal_id).first()
    if not signal:
        return {"signal_id": signal_id}

    return {
        "signal_id": signal.signal_id,
        "drug_name": signal.drug_name,
        "event_name": signal.event_name,
        "report_count": signal.supporting_report_count,
        "prr": signal.prr,
        "priority_level": signal.priority_level,
        "review_areas": [
            "Product Label",
            "PSUR / PBRER",
            "Risk Management Plan (RMP)",
            "Reference Safety Information (RSI)",
        ],
    }


def analyze_document_content(
    db: Session,
    document_id: str,
    gemini_client: Optional[GeminiClient] = None,
    settings: Optional[Settings] = None,
) -> GeminiAnalysis:
    """
    Perform Gemini document intelligence analysis on extracted text of an uploaded document.
    """
    doc = db.query(DocumentUploadModel).filter(DocumentUploadModel.document_id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found.",
        )

    if not doc.extracted_text or not doc.extracted_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Document '{document_id}' does not contain any extracted text for analysis.",
        )

    app_settings = settings or get_settings()
    client = gemini_client or GeminiClient(api_key=app_settings.gemini_api_key)

    if not client.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GEMINI_API_KEY is not configured. Gemini Document Analysis is currently unavailable.",
        )

    signal_context = get_signal_context(db, doc.signal_id)

    try:
        raw_analysis = client.analyze_document(
            document_text=doc.extracted_text,
            document_filename=doc.filename,
            signal_context=signal_context,
        )
    except GeminiAuthError as exc:
        logger.error("Gemini authentication failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gemini authentication failed. Please check GEMINI_API_KEY configuration.",
        ) from exc
    except GeminiAPIError as exc:
        logger.error("Gemini API error during document %s analysis: %s", document_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to retrieve AI document analysis from Gemini service.",
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error during document analysis: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while analyzing document.",
        ) from exc

    # Persist analysis in document_analysis table
    now_utc = datetime.now(timezone.utc)
    analysis_id = f"anl-{document_id}-{int(now_utc.timestamp())}"
    prompt_hash = hashlib.sha256(
        json.dumps(
            {
                "doc_id": document_id,
                "text_snippet": doc.extracted_text[:500],
                "signal": signal_context,
            },
            sort_keys=True,
        ).encode()
    ).hexdigest()

    relevant_sections_models = [
        RelevantSection(
            section_name=sec.get("section_name", "Section"),
            relevance_reason=sec.get("relevance_reason", "Relevance identified"),
        )
        for sec in raw_analysis.get("relevant_sections", [])
    ]

    try:
        analysis_record = DocumentAnalysisModel(
            analysis_id=analysis_id,
            document_id=document_id,
            signal_id=doc.signal_id or "",
            relevant_sections=[s.model_dump() for s in relevant_sections_models],
            existing_related_content=raw_analysis.get("existing_related_content"),
            potential_coverage_gap=raw_analysis.get("potential_coverage_gap"),
            analysis_status=raw_analysis.get("analysis_status", "completed"),
            human_review_required=True,
            model_used=client.model,
            prompt_hash=prompt_hash,
            disclaimer=(
                "AI-assisted document analysis. Identified potential coverage gaps "
                "require professional human review."
            ),
        )
        db.add(analysis_record)
        db.commit()
    except Exception as exc:
        logger.warning("Could not persist DocumentAnalysis record: %s", exc)
        db.rollback()

    return GeminiAnalysis(
        document_id=document_id,
        signal_id=doc.signal_id or "",
        relevant_sections=relevant_sections_models,
        existing_related_content=raw_analysis.get("existing_related_content"),
        potential_coverage_gap=raw_analysis.get("potential_coverage_gap"),
        analysis_status=raw_analysis.get("analysis_status", "completed"),
        human_review_required=True,
        disclaimer=(
            "AI-assisted document analysis. Identified potential coverage gaps "
            "require professional human review."
        ),
    )


def get_document_analysis(db: Session, document_id: str) -> Optional[GeminiAnalysis]:
    """Retrieve the latest stored document analysis for document_id."""
    analysis = (
        db.query(DocumentAnalysisModel)
        .filter(DocumentAnalysisModel.document_id == document_id)
        .order_by(DocumentAnalysisModel.created_at.desc())
        .first()
    )
    if not analysis:
        return None

    sections = [
        RelevantSection(
            section_name=sec.get("section_name", "Section"),
            relevance_reason=sec.get("relevance_reason", "Relevance identified"),
        )
        for sec in (analysis.relevant_sections or [])
    ]

    return GeminiAnalysis(
        document_id=analysis.document_id,
        signal_id=analysis.signal_id,
        relevant_sections=sections,
        existing_related_content=analysis.existing_related_content,
        potential_coverage_gap=analysis.potential_coverage_gap,
        analysis_status=analysis.analysis_status,  # type: ignore
        human_review_required=analysis.human_review_required,
        disclaimer=analysis.disclaimer or (
            "AI-assisted document analysis. Identified potential coverage gaps "
            "require professional human review."
        ),
    )


def get_documents_for_signal(db: Session, signal_id: str) -> List[Dict[str, Any]]:
    """Retrieve all uploaded documents and their analyses associated with a signal."""
    docs = db.query(DocumentUploadModel).filter(DocumentUploadModel.signal_id == signal_id).all()
    results = []
    for doc in docs:
        analysis = get_document_analysis(db, doc.document_id)
        results.append(
            {
                "document": {
                    "document_id": doc.document_id,
                    "filename": doc.filename,
                    "file_type": doc.file_type,
                    "file_size_bytes": doc.file_size_bytes,
                    "signal_id": doc.signal_id,
                    "uploaded_at": doc.created_at,
                    "extracted_text_preview": doc.extracted_text_preview,
                    "status": doc.status,
                },
                "analysis": analysis.model_dump() if analysis else None,
            }
        )
    return results
