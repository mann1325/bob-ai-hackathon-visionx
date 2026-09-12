from datetime import date, datetime, timezone

from shared.schemas.ai import GroqExplanation
from shared.schemas.common import ErrorResponse, PaginatedResponse
from shared.schemas.evidence import DuplicateCandidate
from shared.schemas.regulatory import RegulatoryImpact, ReviewArea
from shared.schemas.signal import DatasetRelease, SignalSummary


def test_signal_summary_schema():
    signal = SignalSummary(
        signal_id="sig-001",
        drug="ASPIRIN",
        event="HEADACHE",
        report_count=42,
        prr=2.5,
        ror=1.8,
        rank=1,
        release_id="2024Q1",
    )
    assert signal.drug == "ASPIRIN"
    assert signal.report_count == 42


def test_duplicate_candidate_never_confirmed_by_default():
    dup = DuplicateCandidate(
        candidate_id="dup-001",
        report_id_a="r1",
        report_id_b="r2",
        rationale="Similar drug, event, and report date within 7 days.",
    )
    assert dup.status == "potential_duplicate"


def test_groq_explanation_requires_human_review():
    explanation = GroqExplanation(
        signal_id="sig-001",
        why_flagged="Elevated PRR with increasing trend.",
        evidence_summary="42 reports support this pair.",
        generated_at=datetime.now(timezone.utc),
    )
    assert explanation.human_review_required is True
    assert "human review" in explanation.disclaimer.lower()


def test_regulatory_impact_schema():
    impact = RegulatoryImpact(
        signal_id="sig-001",
        review_areas=[
            ReviewArea(document_type="Product Label", section_hint="Section 4.8")
        ],
    )
    assert impact.human_review_required is True


def test_paginated_response():
    page = PaginatedResponse[SignalSummary](
        items=[
            SignalSummary(
                signal_id="sig-001",
                drug="ASPIRIN",
                event="HEADACHE",
                report_count=10,
                release_id="2024Q1",
            )
        ],
        total=1,
    )
    assert page.total == 1


def test_error_response():
    err = ErrorResponse(error={"code": "not_found", "message": "Signal not found"})
    assert err.error.code == "not_found"


def test_dataset_release_schema():
    release = DatasetRelease(
        release_id="2024Q1",
        quarter="2024Q1",
        dataset_release="FAERS 2024 Q1",
        import_date=date(2024, 4, 1),
        processing_version="v1.0.0",
    )
    assert release.quarter == "2024Q1"
