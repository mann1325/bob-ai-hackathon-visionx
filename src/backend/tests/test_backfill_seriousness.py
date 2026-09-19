from __future__ import annotations

from zipfile import ZipFile

from sqlalchemy import select
from sqlalchemy.dialects import postgresql

from database.models import ProcessedReportModel
from services.backfill_seriousness import backfill_report_seriousness
from services.backfill_seriousness import _set_based_update_statement


def _write_outc_zip(path, filename: str, rows: list[str]) -> None:
    with ZipFile(path, "w") as archive:
        archive.writestr(filename, "primaryid$caseid$outc_cod\n" + "\n".join(rows) + "\n")


def _seed_reports(db_session):
    reports = [
        ProcessedReportModel(
            report_id="R-DE",
            drug_name="ASPIRIN",
            reactions=["BLEEDING"],
            patient_age=61,
            patient_sex="F",
            event_date="2026-01-01",
            report_quarter="2026Q1",
            source="FDA_FAERS",
        ),
        ProcessedReportModel(
            report_id="R-LT",
            drug_name="ASPIRIN",
            reactions=["BLEEDING"],
            report_quarter="2026Q1",
            source="FDA_FAERS",
        ),
        ProcessedReportModel(
            report_id="R-HO",
            drug_name="ASPIRIN",
            reactions=["BLEEDING"],
            report_quarter="2026Q1",
            source="FDA_FAERS",
        ),
        ProcessedReportModel(
            report_id="R-DS",
            drug_name="ASPIRIN",
            reactions=["BLEEDING"],
            report_quarter="2026Q1",
            source="FDA_FAERS",
        ),
        ProcessedReportModel(
            report_id="R-CA",
            drug_name="ASPIRIN",
            reactions=["BLEEDING"],
            report_quarter="2026Q1",
            source="FDA_FAERS",
        ),
        ProcessedReportModel(
            report_id="R-RI",
            drug_name="ASPIRIN",
            reactions=["BLEEDING"],
            report_quarter="2026Q1",
            source="FDA_FAERS",
        ),
        ProcessedReportModel(
            report_id="R-OT",
            drug_name="ASPIRIN",
            reactions=["BLEEDING"],
            report_quarter="2026Q1",
            source="FDA_FAERS",
        ),
        ProcessedReportModel(
            report_id="R-NON",
            drug_name="ASPIRIN",
            reactions=["BLEEDING"],
            report_quarter="2026Q1",
            source="FDA_FAERS",
        ),
        ProcessedReportModel(
            report_id="R-MISSING",
            drug_name="ASPIRIN",
            reactions=["BLEEDING"],
            report_quarter="2026Q1",
            source="FDA_FAERS",
        ),
        ProcessedReportModel(
            report_id="R-OTHER-QUARTER",
            drug_name="ASPIRIN",
            reactions=["BLEEDING"],
            patient_age=44,
            patient_sex="M",
            event_date="2025-01-01",
            report_quarter="2025Q4",
            source="FDA_FAERS",
            seriousness="Unknown",
            seriousness_codes=[],
        ),
    ]
    db_session.add_all(reports)
    db_session.flush()


def test_backfill_scopes_updates_and_preserves_existing_fields(db_session, tmp_path):
    _seed_reports(db_session)
    zip_path = tmp_path / "faers_ascii_2026q1.zip"
    _write_outc_zip(
        zip_path,
        "ASCII/OUTC26Q1.txt",
        [
            "R-DE$C1$DE",
            "R-DE$C1$HO",
            "R-LT$C2$LT",
            "R-HO$C3$HO",
            "R-DS$C4$DS",
            "R-CA$C5$CA",
            "R-RI$C6$RI",
            "R-OT$C7$OT",
            "R-NON$C8$ZZ",
        ],
    )
    before = db_session.get(ProcessedReportModel, "R-DE")
    original_fields = (before.drug_name, before.reactions, before.patient_age, before.patient_sex, before.event_date, before.source)
    other_before = db_session.get(ProcessedReportModel, "R-OTHER-QUARTER")

    result = backfill_report_seriousness(db_session, zip_path, "2026Q1")
    db_session.expire_all()

    assert result.reports_scoped == 9
    assert result.reports_updated == 8
    assert result.serious == 7
    assert result.non_serious == 1
    assert result.unknown == 1
    assert [db_session.get(ProcessedReportModel, f"R-{code}").seriousness for code in ["DE", "LT", "HO", "DS", "CA", "RI", "OT"]] == ["Serious"] * 7
    assert db_session.get(ProcessedReportModel, "R-DE").seriousness_codes == ["DE", "HO"]
    assert db_session.get(ProcessedReportModel, "R-NON").seriousness == "Non-serious"
    assert db_session.get(ProcessedReportModel, "R-NON").seriousness_codes == []
    assert db_session.get(ProcessedReportModel, "R-MISSING").seriousness == "Unknown"
    assert db_session.get(ProcessedReportModel, "R-MISSING").seriousness_codes == []
    assert (before.drug_name, before.reactions, before.patient_age, before.patient_sex, before.event_date, before.source) == original_fields
    assert (other_before.report_quarter, other_before.seriousness, other_before.seriousness_codes) == ("2025Q4", "Unknown", [])


def test_backfill_is_idempotent(db_session, tmp_path):
    _seed_reports(db_session)
    zip_path = tmp_path / "faers_ascii_2026q1.zip"
    _write_outc_zip(zip_path, "ASCII/OUTC26Q1.txt", ["R-DE$C1$DE", "R-DE$C1$HO", "R-NON$C2$ZZ"])

    first = backfill_report_seriousness(db_session, zip_path, "2026Q1")
    first_values = {
        report.report_id: (report.seriousness, report.seriousness_codes)
        for report in db_session.scalars(
            select(ProcessedReportModel).where(ProcessedReportModel.report_quarter == "2026Q1")
        ).all()
    }
    second = backfill_report_seriousness(db_session, zip_path, "2026Q1")
    second_values = {
        report.report_id: (report.seriousness, report.seriousness_codes)
        for report in db_session.scalars(
            select(ProcessedReportModel).where(ProcessedReportModel.report_quarter == "2026Q1")
        ).all()
    }

    assert first.quarter == second.quarter
    assert first.serious == second.serious
    assert first.non_serious == second.non_serious
    assert first.unknown == second.unknown
    assert second.reports_updated == 0
    assert first_values == second_values


def test_backfill_skips_already_correct_rows_and_changes_only_seriousness_fields(db_session, tmp_path):
    _seed_reports(db_session)
    correct = db_session.get(ProcessedReportModel, "R-DE")
    correct.seriousness = "Serious"
    correct.seriousness_codes = ["DE", "HO"]
    non_correct = db_session.get(ProcessedReportModel, "R-NON")
    non_correct.seriousness = "Serious"
    non_correct.seriousness_codes = ["DE"]
    db_session.flush()

    zip_path = tmp_path / "faers_ascii_2026q1.zip"
    _write_outc_zip(zip_path, "ASCII/OUTC26Q1.txt", ["R-DE$C1$DE", "R-DE$C1$HO"])

    result = backfill_report_seriousness(db_session, zip_path, "2026Q1")
    db_session.expire_all()

    assert result.reports_updated == 1
    assert correct.seriousness == "Serious"
    assert correct.seriousness_codes == ["DE", "HO"]


def test_backfill_batching_preserves_results(db_session, tmp_path):
    _seed_reports(db_session)
    zip_path = tmp_path / "faers_ascii_2026q1.zip"
    _write_outc_zip(zip_path, "ASCII/OUTC26Q1.txt", ["R-DE$C1$DE", "R-NON$C2$ZZ"])

    result = backfill_report_seriousness(db_session, zip_path, "2026Q1")

    assert result.reports_scoped == 9
    assert db_session.get(ProcessedReportModel, "R-DE").seriousness_codes == ["DE"]
    assert db_session.get(ProcessedReportModel, "R-NON").seriousness == "Non-serious"


def test_set_based_update_compiles_one_values_update_for_multiple_rows():
    statement = _set_based_update_statement(
        [
            {
                "report_id": "R-1",
                "report_quarter": "2026Q1",
                "seriousness": "Serious",
                "seriousness_codes": ["DE"],
            },
            {
                "report_id": "R-2",
                "report_quarter": "2026Q1",
                "seriousness": "Non-serious",
                "seriousness_codes": [],
            },
        ]
    )
    sql = str(statement.compile(dialect=postgresql.dialect()))

    assert "UPDATE processed_reports" in sql
    assert "FROM (VALUES" in sql
    assert sql.count("UPDATE processed_reports") == 1
    assert "report_quarter" in sql
    assert "seriousness_codes" in sql
    assert "updated_at" not in sql