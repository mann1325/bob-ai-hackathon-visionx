import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from fastapi import HTTPException
from sqlalchemy.orm import Session

from ai.groq_client import (
    DEFAULT_GROQ_MODEL,
    GroqAPIError,
    GroqAuthError,
    GroqClient,
)
from app.config import get_settings
from database.models import AISummaryModel
from services.signal_service import get_signal_evidence
from shared.schemas.ai import GroqExplanation

logger = logging.getLogger(__name__)

_DUPLICATE_RATIONALE_SAMPLE_SIZE = 3


def generate_signal_explanation(
    db: Session,
    signal_id: str,
    groq_client: Optional[GroqClient] = None,
) -> Optional[GroqExplanation]:
    """Generate structured evidence explanation using Groq with backend facts only."""
    evidence = get_signal_evidence(db, signal_id)
    if not evidence:
        return None

    settings = get_settings()
    client = groq_client or GroqClient(api_key=settings.groq_api_key)

    if not client.is_configured:
        raise HTTPException(
            status_code=503,
            detail="GROQ_API_KEY is not configured. Groq AI evidence explanation is currently unavailable.",
        )

    # Collect backend-computed structured facts ONLY (no raw FAERS rows)
    facts: Dict[str, Any] = {
        "drug_name": evidence.drug_name,
        "event_name": evidence.event_name,
        "report_count": evidence.metrics.get("report_count", 0),
        "prr": evidence.metrics.get("prr", "N/A"),
        "ror": evidence.metrics.get("ror", "N/A"),
        "trend_score": evidence.metrics.get("trend_score", "N/A"),
        "quality_score": (
            evidence.case_quality.quality_score if evidence.case_quality else "N/A"
        ),
        "quality_flags": (
            evidence.case_quality.quality_flags if evidence.case_quality else []
        ),
        "duplicate_count": len(evidence.potential_duplicates),
        "duplicate_rationale_sample": [
            d.rationale
            for d in evidence.potential_duplicates[:_DUPLICATE_RATIONALE_SAMPLE_SIZE]
            if d.rationale
        ],
        "known_limitations": evidence.known_limitations,
    }

    try:
        explanation_data = client.generate_explanation(facts)
    except GroqAuthError as exc:
        logger.error("Groq authentication error: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Groq authentication failed. Please check GROQ_API_KEY configuration.",
        ) from exc
    except GroqAPIError as exc:
        logger.error("Groq API error for signal %s: %s", signal_id, exc)
        raise HTTPException(
            status_code=502,
            detail="Failed to retrieve AI explanation from Groq service.",
        ) from exc
    except Exception as exc:
        logger.exception("Unexpected error during Groq explanation: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while generating explanation.",
        ) from exc

    now_utc = datetime.now(timezone.utc)
    summary_id = f"exp-{signal_id}-{int(now_utc.timestamp())}"
    prompt_hash = hashlib.sha256(json.dumps(facts, sort_keys=True).encode()).hexdigest()

    # Persist summary for audit trail
    try:
        ai_summary = AISummaryModel(
            summary_id=summary_id,
            signal_id=signal_id,
            why_flagged=explanation_data["why_flagged"],
            evidence_summary=explanation_data["evidence_summary"],
            limitations=explanation_data["limitations"],
            suggested_questions=explanation_data["suggested_questions"],
            model_used=client.model,
            prompt_hash=prompt_hash,
        )
        db.add(ai_summary)
        db.flush()
    except Exception as exc:
        logger.warning("Could not persist AI summary audit record: %s", exc)

    return GroqExplanation(
        signal_id=signal_id,
        why_flagged=explanation_data["why_flagged"],
        evidence_summary=explanation_data["evidence_summary"],
        limitations=explanation_data["limitations"],
        suggested_questions=explanation_data["suggested_questions"],
        generated_at=now_utc,
        model_used=client.model,
        human_review_required=True,
        disclaimer=(
            "AI-generated explanation for decision support. "
            "Does not establish causality or replace professional human review."
        ),
    )
