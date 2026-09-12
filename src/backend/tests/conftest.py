from datetime import date, datetime, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.dependencies import get_db
from app.main import create_app
from database.base import Base
from database.models import (
    CaseQualityModel,
    DrugEventPairModel,
    DuplicateCandidateModel,
    FAERSQuarterlyMetadataModel,
    ProcessedReportModel,
    SignalMetricsModel,
    SignalModel,
)


@pytest.fixture(scope="session")
def test_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def db_session(test_engine):
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    # Seed test dataset releases
    session.add_all(
        [
            FAERSQuarterlyMetadataModel(
                release_id="2024Q1",
                quarter="2024Q1",
                dataset_release="FAERS 2024 Q1",
                import_date=date(2024, 4, 1),
                processing_version="v1.0.0",
                total_reports=1500000,
                processed_at=datetime(2024, 4, 2, 10, 0, tzinfo=timezone.utc),
            ),
            FAERSQuarterlyMetadataModel(
                release_id="2023Q4",
                quarter="2023Q4",
                dataset_release="FAERS 2023 Q4",
                import_date=date(2024, 1, 15),
                processing_version="v1.0.0",
                total_reports=1400000,
                processed_at=datetime(2024, 1, 16, 10, 0, tzinfo=timezone.utc),
            ),
        ]
    )

    # Seed test signals
    session.add_all(
        [
            SignalModel(
                signal_id="sig-001",
                drug_name="ASPIRIN",
                event_name="GASTROINTESTINAL BLEEDING",
                supporting_report_count=120,
                prr=3.4,
                ror=2.8,
                trend_score=0.85,
                risk_score=0.75,
                priority_level="high",
                candidate_status="candidate",
                dataset_version="2024Q1",
                rank=1,
                known_limitations=["Spontaneous report bias", "Known label association"],
            ),
            SignalModel(
                signal_id="sig-002",
                drug_name="WARFARIN",
                event_name="HAEMORRHAGE",
                supporting_report_count=85,
                prr=2.9,
                ror=2.2,
                trend_score=0.60,
                risk_score=0.65,
                priority_level="medium",
                candidate_status="under_review",
                dataset_version="2024Q1",
                rank=2,
            ),
            SignalModel(
                signal_id="sig-003",
                drug_name="METFORMIN",
                event_name="LACTIC ACIDOSIS",
                supporting_report_count=45,
                prr=2.1,
                ror=1.7,
                trend_score=0.40,
                risk_score=0.50,
                priority_level="low",
                candidate_status="closed",
                dataset_version="2023Q4",
                rank=3,
            ),
        ]
    )

    # Seed metrics
    session.add(
        SignalMetricsModel(
            signal_id="sig-001",
            prr=3.4,
            ror=2.8,
            report_count=120,
            contingency_table={"a": 120, "b": 500, "c": 300, "d": 20000},
            trend_data=[
                {"quarter": "2023Q3", "count": 25},
                {"quarter": "2023Q4", "count": 40},
                {"quarter": "2024Q1", "count": 55},
            ],
            chi_square=45.2,
        )
    )

    # Seed case quality
    session.add(
        CaseQualityModel(
            signal_id="sig-001",
            total_reports=120,
            missing_age_count=12,
            missing_sex_count=5,
            missing_date_count=8,
            quality_score=0.88,
            quality_flags=["minor_missing_dates"],
            indicators=[
                {"flag": "missing_age", "description": "10% reports missing age", "impact_level": "low"}
            ],
        )
    )

    # Seed duplicate candidate
    session.add(
        DuplicateCandidateModel(
            candidate_id="dup-001",
            signal_id="sig-001",
            report_id_a="r-101",
            report_id_b="r-102",
            rationale="Identical drug, event, age 62M, within 3 days.",
            similarity_score=0.92,
            drug_similarity=1.0,
            event_similarity=1.0,
            date_proximity_days=3,
            matched_fields=["drug", "event", "age", "sex"],
            status="potential_duplicate",
        )
    )

    # Seed processed report for search fallback
    session.add(
        ProcessedReportModel(
            report_id="rep-999",
            drug_name="LISINOPRIL",
            reactions=["COUGH"],
            report_quarter="2024Q1",
        )
    )

    session.flush()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session) -> TestClient:
    app = create_app()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)
