from typing import Any, Dict, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db
from services.signal_service import search_drugs

router = APIRouter(prefix="/drugs", tags=["drugs"])


@router.get("/search")
def search_drug_names(
    q: str = Query(..., min_length=1, description="Drug name search term"),
    limit: int = Query(20, ge=1, le=100, description="Max results to return"),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Search for drug names against processed pharmacovigilance data."""
    return search_drugs(db, query=q, limit=limit)
