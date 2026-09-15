from typing import List, Optional
from pydantic import BaseModel, Field


class ReviewArea(BaseModel):
    document_type: str
    section_hint: Optional[str] = None
    rationale: Optional[str] = None
    priority: Optional[str] = "medium"


class RuleMatch(BaseModel):
    rule_id: str
    rule_name: str
    condition_matched: str
    review_area: ReviewArea
    confidence_rationale: Optional[str] = None


class RuleDefinition(BaseModel):
    rule_id: str
    rule_name: str
    description: str
    target_document_type: str
    section_hint: Optional[str] = None
    default_priority: str = "medium"


class RegulatoryImpact(BaseModel):
    signal_id: str
    review_areas: List[ReviewArea] = Field(default_factory=list)
    rule_matches: List[RuleMatch] = Field(default_factory=list)
    human_review_required: bool = True
    disclaimer: str = (
        "Deterministic regulatory mapping for triage guidance only. "
        "Final regulatory determinations require qualified professional review."
    )
