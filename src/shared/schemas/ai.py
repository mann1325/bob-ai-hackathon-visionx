from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class GroqExplanation(BaseModel):
    signal_id: str
    why_flagged: str
    evidence_summary: str
    limitations: List[str] = Field(default_factory=list)
    suggested_questions: List[str] = Field(default_factory=list)
    generated_at: Optional[datetime] = None
    model_used: Optional[str] = None
    human_review_required: bool = True
    disclaimer: str = (
        "AI-generated explanation for decision support. "
        "Does not establish causality or replace human review."
    )


class RelevantSection(BaseModel):
    section_name: str
    relevance_reason: str


class GeminiAnalysis(BaseModel):
    document_id: str
    signal_id: str
    relevant_sections: List[RelevantSection] = Field(default_factory=list)
    existing_related_content: Optional[str] = None
    potential_coverage_gap: Optional[str] = None
    analysis_status: Literal["completed", "needs_review", "failed"] = "completed"
    human_review_required: bool = True
    disclaimer: str = (
        "AI-assisted document analysis. Identified potential coverage gaps "
        "require professional human review."
    )
