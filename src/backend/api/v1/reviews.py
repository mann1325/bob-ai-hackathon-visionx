from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_db
from services.review_service import get_signal_review, save_signal_review
from shared.schemas.review import ReviewResponse, ReviewUpdate

router = APIRouter(prefix="/signals/{signal_id}/review", tags=["reviews"])


@router.get("", response_model=ReviewResponse)
def get_review(signal_id: str, db: Session = Depends(get_db)) -> ReviewResponse:
    review = get_signal_review(db, signal_id)
    if review is None:
        raise HTTPException(status_code=404, detail=f"Signal '{signal_id}' not found.")
    return review


@router.put("", response_model=ReviewResponse)
def put_review(
    signal_id: str,
    payload: ReviewUpdate,
    db: Session = Depends(get_db),
) -> ReviewResponse:
    review = save_signal_review(db, signal_id, payload)
    if review is None:
        raise HTTPException(status_code=404, detail=f"Signal '{signal_id}' not found.")
    db.commit()
    return review