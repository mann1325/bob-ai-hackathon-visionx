from datetime import datetime
from typing import Dict, Optional, Literal

from pydantic import BaseModel, Field


ReviewStatus = Literal["not_started", "in_review", "reviewed"]

CHECKLIST_KEYS = (
    "supporting_reports_reviewed",
    "case_quality_reviewed",
    "reporting_trend_reviewed",
    "duplicates_reviewed",
    "ai_explanation_reviewed",
    "regulatory_documents_reviewed",
)


class EvidenceChecklist(BaseModel):
    supporting_reports_reviewed: bool = False
    case_quality_reviewed: bool = False
    reporting_trend_reviewed: bool = False
    duplicates_reviewed: bool = False
    ai_explanation_reviewed: bool = False
    regulatory_documents_reviewed: bool = False


class ReviewUpdate(BaseModel):
    review_status: ReviewStatus = "not_started"
    evidence_checklist: EvidenceChecklist = Field(default_factory=EvidenceChecklist)
    reviewer_notes: str = ""
    reviewer_conclusion: str = ""


class ReviewResponse(ReviewUpdate):
    review_id: Optional[str] = None
    signal_id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
