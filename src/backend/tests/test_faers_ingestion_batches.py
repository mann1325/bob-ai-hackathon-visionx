from datetime import date
import zipfile

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import services.faers_ingestion_service as ingestion
from database.base import Base
from database.models import (
    DrugEventPairModel,
    FAERSQuarterlyMetadataModel,
    ProcessedReportModel,
)


@pytest.fixture
def ingestion_db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'ingestion.db'}")
    Base.metadata.create_all(bind=engine)
    with Session(engine) as session:
        session.add(
            ProcessedReportModel(
                report_id="existing-2026q1",
                drug_name="ASPIRIN",
                reactions=["HEADACHE"],
                report_quarter="2026Q1",
                source="FDA_FAERS",
            )
        )
        session.commit()
        yield session


def _write_zip(path, report_count=5):
    demo_rows = ["primaryid$caseid$caseversion$i_f_code$event_dt$age$age_cod$sex"]
    drug_rows = ["primaryid$caseid$drug_seq$role_cod$drugname"]
    reac_rows = ["primaryid$caseid$pt"]
    outc_rows = ["primaryid$caseid$outc_cod"]
    for index in range(report_count):
        report_id = f"report-{index}"
        demo_rows.append(f"{report_id}$case-{index}$1$F$20251001$40$801$1")
        drug_rows.append(f"{report_id}$case-{index}$1$PS$ASPIRIN")
        reac_rows.append(f"{report_id}$case-{index}$HEADACHE")
        outc_rows.append(f"{report_id}$case-{index}$OT")

    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("ASCII/DEMO25Q4.txt", "\n".join(demo_rows))
        archive.writestr("ASCII/DRUG25Q4.txt", "\n".join(drug_rows))
        archive.writestr("ASCII/REAC25Q4.txt", "\n".join(reac_rows))
        archive.writestr("ASCII/OUTC25Q4.txt", "\n".join(outc_rows))


def _quarter_reports(session, quarter):
    return session.scalars(
        select(ProcessedReportModel).where(
            ProcessedReportModel.report_quarter == quarter
        )
    ).all()


def test_ingestion_commits_bounded_batches_and_isolates_2026q1(
    ingestion_db, tmp_path, monkeypatch
):
    zip_path = tmp_path / "faers_ascii_2025q4.zip"
    _write_zip(zip_path, report_count=5)
    monkeypatch.setattr(ingestion, "INGESTION_BATCH_SIZE", 2)

    inserted, _ = ingestion.ingest_faers_zip(
        ingestion_db, "2025Q4", str(zip_path)
    )

    assert inserted == 5
    assert len(_quarter_reports(ingestion_db, "2025Q4")) == 5
    assert len(_quarter_reports(ingestion_db, "2026Q1")) == 1
    assert ingestion_db.scalar(
        select(FAERSQuarterlyMetadataModel).where(
            FAERSQuarterlyMetadataModel.release_id == "2025Q4"
        )
    ).total_reports == 5


def test_ingestion_rerun_is_idempotent(ingestion_db, tmp_path):
    zip_path = tmp_path / "faers_ascii_2025q4.zip"
    _write_zip(zip_path, report_count=3)

    ingestion.ingest_faers_zip(ingestion_db, "2025Q4", str(zip_path))

    with pytest.raises(ingestion.FAERSAlreadyImportedError):
        ingestion.ingest_faers_zip(ingestion_db, "2025Q4", str(zip_path))

    assert len(_quarter_reports(ingestion_db, "2025Q4")) == 3
    assert ingestion_db.scalar(
        select(DrugEventPairModel.count).where(
            DrugEventPairModel.quarter == "2025Q4",
            DrugEventPairModel.drug_name == "ASPIRIN",
            DrugEventPairModel.event_name == "HEADACHE",
        )
    ) == 3


def test_ingestion_failure_can_resume_without_duplicates(
    ingestion_db, tmp_path, monkeypatch
):
    zip_path = tmp_path / "faers_ascii_2025q4.zip"
    _write_zip(zip_path, report_count=5)
    monkeypatch.setattr(ingestion, "INGESTION_BATCH_SIZE", 2)
    original_commit = ingestion._commit_report_batch
    calls = {"count": 0}

    def fail_second_batch(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 2:
            raise RuntimeError("simulated batch failure")
        return original_commit(*args, **kwargs)

    monkeypatch.setattr(ingestion, "_commit_report_batch", fail_second_batch)
    with pytest.raises(RuntimeError, match="simulated batch failure"):
        ingestion.ingest_faers_zip(ingestion_db, "2025Q4", str(zip_path))

    assert len(_quarter_reports(ingestion_db, "2025Q4")) == 2
    assert ingestion_db.scalar(
        select(FAERSQuarterlyMetadataModel).where(
            FAERSQuarterlyMetadataModel.release_id == "2025Q4"
        )
    ) is None

    monkeypatch.setattr(ingestion, "_commit_report_batch", original_commit)
    inserted, _ = ingestion.ingest_faers_zip(
        ingestion_db, "2025Q4", str(zip_path)
    )

    assert inserted == 3
    assert len(_quarter_reports(ingestion_db, "2025Q4")) == 5
    assert len({report.report_id for report in _quarter_reports(ingestion_db, "2025Q4")}) == 5
    assert len(_quarter_reports(ingestion_db, "2026Q1")) == 1
