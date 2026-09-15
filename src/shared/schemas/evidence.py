from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DuplicateCandidate(BaseModel):
    candidate_id: str
    report_id_a: str
    report_id_b: str
    rationale: str
    status: str = "potential_duplicate"
    similarity_score: Optional[float] = None
    drug_similarity: Optional[float] = None
    event_similarity: Optional[float] = None
    date_proximity_days: Optional[int] = None
    matched_fields: List[str] = Field(default_factory=list)
    human_review_required: bool = True
    disclaimer: str = (
        "Candidate duplicate flagged for human triage only. "
        "Automated deletion is strictly prohibited."
    )


class CaseQualityIndicator(BaseModel):
    flag: str
    description: str
    impact_level: str = "medium"


class CaseQualityReport(BaseModel):
    signal_id: str
    total_reports: int = 0
    missing_age_count: int = 0
    missing_sex_count: int = 0
    missing_date_count: int = 0
    quality_score: float = 1.0
    quality_flags: List[str] = Field(default_factory=list)
    indicators: List[CaseQualityIndicator] = Field(default_factory=list)


class EvidenceBundle(BaseModel):
    signal_id: str
    drug_name: str
    event_name: str
    metrics: Dict[str, Any] = Field(default_factory=dict)
    case_quality: Optional[CaseQualityReport] = None
    potential_duplicates: List[DuplicateCandidate] = Field(default_factory=list)
    known_limitations: List[str] = Field(default_factory=list)
    human_review_required: bool = True
