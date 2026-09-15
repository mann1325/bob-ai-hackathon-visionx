from datetime import date
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, model_validator


class CandidateStatus(str, Enum):
    CANDIDATE = "candidate"
    UNDER_REVIEW = "under_review"
    CLOSED = "closed"


class PriorityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DatasetRelease(BaseModel):
    release_id: str
    quarter: str
    dataset_release: str
    import_date: date
    processing_version: str
    total_reports: Optional[int] = None
    processed_at: Optional[str] = None


class NormalizedReport(BaseModel):
    report_id: str
    drug_name: str
    reactions: List[str]
    patient_age: Optional[float] = None
    patient_sex: Optional[str] = None
    event_date: Optional[str] = None
    report_quarter: str
    source: str = "FDA_FAERS"


class SignalSummary(BaseModel):
    signal_id: str
    drug_name: str = ""
    event_name: str = ""
    supporting_report_count: int = Field(default=0, ge=0)
    prr: float = 0.0
    ror: Optional[float] = None
    trend_score: Optional[float] = None
    risk_score: Optional[float] = None
    priority_level: Optional[Literal["low", "medium", "high", "critical"]] = None
    candidate_status: Literal["candidate", "under_review", "closed"] = "candidate"
    dataset_version: Optional[str] = None
    rank: Optional[int] = None

    @model_validator(mode="before")
    @classmethod
    def populate_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "drug" in data and "drug_name" not in data:
                data["drug_name"] = data["drug"]
            elif "drug_name" in data and "drug" not in data:
                data["drug"] = data["drug_name"]

            if "event" in data and "event_name" not in data:
                data["event_name"] = data["event"]
            elif "event_name" in data and "event" not in data:
                data["event"] = data["event_name"]

            if "report_count" in data and "supporting_report_count" not in data:
                data["supporting_report_count"] = data["report_count"]
            elif "supporting_report_count" in data and "report_count" not in data:
                data["report_count"] = data["supporting_report_count"]

            if "release_id" in data and "dataset_version" not in data:
                data["dataset_version"] = data["release_id"]
            elif "dataset_version" in data and "release_id" not in data:
                data["release_id"] = data["dataset_version"]
        return data

    @property
    def drug(self) -> str:
        return self.drug_name

    @property
    def event(self) -> str:
        return self.event_name

    @property
    def report_count(self) -> int:
        return self.supporting_report_count

    @property
    def release_id(self) -> Optional[str]:
        return self.dataset_version


class SignalMetrics(BaseModel):
    signal_id: str
    prr: float
    ror: Optional[float] = None
    report_count: int = Field(ge=0)
    contingency_table: Optional[Dict[str, int]] = None
    trend_data: Optional[List[Dict[str, Any]]] = None
    chi_square: Optional[float] = None


class SignalDetail(BaseModel):
    signal_id: str
    drug_name: str
    event_name: str
    supporting_report_count: int
    prr: float
    ror: Optional[float] = None
    trend_score: Optional[float] = None
    risk_score: Optional[float] = None
    priority_level: Optional[Literal["low", "medium", "high", "critical"]] = None
    candidate_status: Literal["candidate", "under_review", "closed"] = "candidate"
    dataset_version: Optional[str] = None
    dataset_source: Optional[str] = None
    processing_version: Optional[str] = None
    import_date: Optional[date] = None
    metrics: Optional[SignalMetrics] = None
    known_limitations: List[str] = Field(default_factory=list)
    human_review_required: bool = True
    disclaimer: str = (
        "Candidate signal only. Does not establish causality or drug safety conclusion. "
        "Requires professional pharmacovigilance review."
    )
