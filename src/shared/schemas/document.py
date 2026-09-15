from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field

from shared.schemas.ai import RelevantSection


class DocumentUpload(BaseModel):
    document_id: str
    filename: str
    file_type: str
    file_size_bytes: int
    signal_id: Optional[str] = None
    uploaded_at: Optional[datetime] = None
    extracted_text_preview: Optional[str] = None
    status: str = "uploaded"


class DocumentAnalysis(BaseModel):
    document_id: str
    signal_id: str
    relevant_sections: List[RelevantSection] = Field(default_factory=list)
    existing_related_content: Optional[str] = None
    potential_coverage_gap: Optional[str] = None
    analysis_status: Literal["completed", "needs_review", "failed"] = "completed"
    human_review_required: bool = True
