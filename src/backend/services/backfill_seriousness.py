"""Backfill stored processed reports from official FAERS OUTC data."""

from __future__ import annotations

import argparse
import logging
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import List

from sqlalchemy import (
    JSON,
    Column,
    MetaData,
    String,
    Table,
    column,
    literal,
    select,
    union_all,
    update,
    values,
)
from sqlalchemy.orm import Session

from database.models import ProcessedReportModel
from database.session import get_session_factory
from services.faers_ingestion_service import (
    _seriousness_for_outcomes,
    parse_outc_file,
)

logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[BACKFILL] %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False

BATCH_SIZE = 2000

REPORTS_UPDATE_TABLE = Table(
    "processed_reports",
    MetaData(),
    Column("report_id", String(50)),
    Column("report_quarter", String(20)),
    Column("seriousness", String(20)),
    Column("seriousness_codes", JSON),
)


def _set_based_update_statement(updates: list[dict], dialect_name: str = "postgresql"):
    """Build one parameterized UPDATE ... FROM (VALUES ...) statement."""
    if dialect_name == "sqlite":
        rows = [
            select(
                literal(row["report_id"], String(50)).label("report_id"),
                literal(row["report_quarter"], String(20)).label("report_quarter"),
                literal(row["seriousness"], String(20)).label("seriousness"),
                literal(row["seriousness_codes"], JSON).label("seriousness_codes"),
            )
            for row in updates
        ]
        outcome_values = union_all(*rows).subquery("v")
    else:
        outcome_values = values(
            column("report_id", String(50)),
            column("report_quarter", String(20)),
            column("seriousness", String(20)),
            column("seriousness_codes", JSON),
            name="backfill_values",
        ).data(
            [
                (
                    row["report_id"],
                    row["report_quarter"],
                    row["seriousness"],
                    row["seriousness_codes"],
                )
                for row in updates
            ]
        ).alias("v")
    reports = REPORTS_UPDATE_TABLE
    return (
        update(reports)
        .where(
            reports.c.report_id == outcome_values.c.report_id,
            reports.c.report_quarter == outcome_values.c.report_quarter,
        )
        .values(
            seriousness=outcome_values.c.seriousness,
            seriousness_codes=outcome_values.c.seriousness_codes,
        )
    )


@dataclass(frozen=True)
class BackfillResult:
    quarter: str
    outc_records: int
    reports_scoped: int
    reports_updated: int
    serious: int
    non_serious: int
    unknown: int


def _read_outc_from_zip(zip_path: str | Path, quarter: str) -> tuple[dict[str, List[str]], int]:
    """Read only the quarter's OUTC member from an official FAERS ZIP."""
    read_started = time.perf_counter()
    logger.info("OUTC read started")
    expected_name = f"OUTC{quarter[2:4]}Q{quarter[-1]}.TXT".upper()
    with zipfile.ZipFile(zip_path, "r") as archive:
        members = [
            name
            for name in archive.namelist()
            if Path(name).name.upper() == expected_name
        ]
        if not members:
            raise FileNotFoundError(
                f"{expected_name} not found in FAERS ZIP '{zip_path}'."
            )

        with archive.open(members[0], "r") as member:
            content = member.read().decode("utf-8", errors="replace")
    logger.info("OUTC read completed: %.2fs", time.perf_counter() - read_started)

    parse_started = time.perf_counter()
    outcome_map = parse_outc_file(content)
    outc_records = sum(len(codes) for codes in outcome_map.values())
    logger.info(
        "OUTC parse completed: %.2fs primaryids=%d outc_records=%d",
        time.perf_counter() - parse_started,
        len(outcome_map),
        outc_records,
    )
    return outcome_map, outc_records


def backfill_report_seriousness(
    db: Session,
    zip_path: str | Path,
    quarter: str,
) -> BackfillResult:
    """Update seriousness fields for existing reports in one quarter only.

    The caller owns the transaction. This function never inserts or deletes
    reports and changes only ``seriousness`` and ``seriousness_codes``.
    """
    release_id = quarter.strip().upper()
    if len(release_id) != 6 or release_id[4] != "Q":
        raise ValueError("quarter must use the YYYYQn format, for example 2026Q1")

    outcome_map, outc_records = _read_outc_from_zip(zip_path, release_id)
    counts = {"Serious": 0, "Non-serious": 0, "Unknown": 0}
    matched = 0
    updated = 0
    report_query = (
        select(
            ProcessedReportModel.report_id,
            ProcessedReportModel.seriousness,
            ProcessedReportModel.seriousness_codes,
        )
        .where(ProcessedReportModel.report_quarter == release_id)
        .order_by(ProcessedReportModel.report_id)
        .execution_options(stream_results=True, yield_per=BATCH_SIZE)
    )

    select_started = time.perf_counter()
    logger.info("SELECT started")
    result = db.execute(report_query)
    logger.info("SELECT execute completed: %.2fs", time.perf_counter() - select_started)
    first_fetch = True
    while True:
        fetch_started = time.perf_counter()
        if first_fetch:
            logger.info("first fetch started")
        batch = result.fetchmany(BATCH_SIZE)
        if first_fetch:
            logger.info(
                "first fetch completed: %.2fs rows=%d",
                time.perf_counter() - fetch_started,
                len(batch),
            )
            first_fetch = False
        if not batch:
            break

        updates = []
        for report_id, current_seriousness, current_codes in batch:
            if report_id in outcome_map:
                seriousness, seriousness_codes = _seriousness_for_outcomes(
                    outcome_map[report_id]
                )
            else:
                seriousness, seriousness_codes = "Unknown", []

            matched += 1
            counts[seriousness] += 1
            if (
                current_seriousness == seriousness
                and (current_codes or []) == seriousness_codes
            ):
                continue

            updates.append(
                {
                    "report_id": report_id,
                    "report_quarter": release_id,
                    "seriousness": seriousness,
                    "seriousness_codes": seriousness_codes,
                }
            )

        if updates:
            update_started = time.perf_counter()
            logger.info("batch update started: rows=%d", len(updates))
            db.execute(
                _set_based_update_statement(
                    updates,
                    db.get_bind().dialect.name,
                )
            )
            updated += len(updates)
            logger.info(
                "batch update completed: %.2fs rows=%d",
                time.perf_counter() - update_started,
                len(updates),
            )

        logger.info(
            "batch progress: quarter=%s processed=%d matched=%d updated=%d",
            release_id,
            matched,
            matched,
            updated,
        )

    flush_started = time.perf_counter()
    logger.info("flush started")
    db.flush()
    logger.info("flush completed: %.2fs", time.perf_counter() - flush_started)
    return BackfillResult(
        quarter=release_id,
        outc_records=outc_records,
        reports_scoped=matched,
        reports_updated=updated,
        serious=counts["Serious"],
        non_serious=counts["Non-serious"],
        unknown=counts["Unknown"],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill report seriousness from FAERS OUTC data.")
    parser.add_argument("--zip-path", required=True)
    parser.add_argument("--quarter", required=True)
    args = parser.parse_args()

    factory = get_session_factory()
    if factory is None:
        raise RuntimeError("Database connection is not configured or unavailable.")

    db = factory()
    try:
        result = backfill_report_seriousness(db, args.zip_path, args.quarter)
        commit_started = time.perf_counter()
        logger.info("commit started")
        db.commit()
        logger.info("commit completed: %.2fs", time.perf_counter() - commit_started)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print(
        "Backfill completed: "
        f"quarter={result.quarter} matched={result.reports_scoped} "
        f"updated={result.reports_updated} "
        f"serious={result.serious} non_serious={result.non_serious} "
        f"unknown={result.unknown}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())