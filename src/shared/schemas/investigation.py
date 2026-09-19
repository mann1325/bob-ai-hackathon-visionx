from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from shared.schemas.review import EvidenceChecklist, ReviewStatus


class InvestigationDocumentSummary(BaseModel):
    document_id: str
    filename: str
    analysis_status: Optional[str] = None
    relevant_section_count: int = 0
    potential_coverage_gap: Optional[str] = None
    human_review_required: bool = True


class InvestigationSummary(BaseModel):
    signal_id: str
    drug_name: str
    event_name: str
    dataset_version: Optional[str] = None
    candidate_status: str
    priority_level: Optional[str] = None
    supporting_report_count: int
    prr: float
    ror: Optional[float] = None
    chi_square: Optional[float] = None
    trend_score: Optional[float] = None
    trend_data: Optional[List[Dict[str, Any]]] = None
    why_flagged: str
    known_limitations: List[str] = Field(default_factory=list)
    case_quality: Optional[Dict[str, Any]] = None
    duplicate_count: int = 0
    duplicates: List[Dict[str, Any]] = Field(default_factory=list)
    ai_explanation: Optional[Dict[str, Any]] = None
    regulatory_review_areas: List[Dict[str, Any]] = Field(default_factory=list)
    regulatory_rule_matches: List[Dict[str, Any]] = Field(default_factory=list)
    documents: List[InvestigationDocumentSummary] = Field(default_factory=list)
    human_review: Optional[Dict[str, Any]] = None
    human_review_required: bool = True
