from __future__ import annotations

from typing import Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import SignalModel, SignalReviewModel
from shared.schemas.review import EvidenceChecklist, ReviewResponse, ReviewUpdate


def _review_response(review: SignalReviewModel | None, signal_id: str) -> ReviewResponse:
    if review is None:
        return ReviewResponse(signal_id=signal_id)
    return ReviewResponse(
        review_id=review.review_id,
        signal_id=review.signal_id,
        review_status=review.review_status,
        evidence_checklist=EvidenceChecklist.model_validate(review.evidence_checklist or {}),
        reviewer_notes=review.reviewer_notes,
        reviewer_conclusion=review.reviewer_conclusion,
        created_at=review.created_at,
        updated_at=review.updated_at,
    )


def get_signal_review(db: Session, signal_id: str) -> Optional[ReviewResponse]:
    if db.scalar(select(SignalModel.signal_id).where(SignalModel.signal_id == signal_id)) is None:
        return None
    review = db.scalars(
        select(SignalReviewModel).where(SignalReviewModel.signal_id == signal_id)
    ).first()
    return _review_response(review, signal_id)


def save_signal_review(
    db: Session, signal_id: str, payload: ReviewUpdate
) -> Optional[ReviewResponse]:
    if db.scalar(select(SignalModel.signal_id).where(SignalModel.signal_id == signal_id)) is None:
        return None

    review = db.scalars(
        select(SignalReviewModel).where(SignalReviewModel.signal_id == signal_id)
    ).first()
    if review is None:
        review = SignalReviewModel(
            review_id=f"REV-{uuid4().hex[:12].upper()}",
            signal_id=signal_id,
        )
        db.add(review)

    review.review_status = payload.review_status
    review.evidence_checklist = payload.evidence_checklist.model_dump()
    review.reviewer_notes = payload.reviewer_notes
    review.reviewer_conclusion = payload.reviewer_conclusion
    db.flush()
    return _review_response(review, signal_id)