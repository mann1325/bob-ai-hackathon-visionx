"""One-time bulk loader for normalized report-level FAERS data.

This utility is intentionally outside the production request path. It loads
the report and pair outputs produced by the existing FAERS pipeline into the
three report-level tables without touching signals or signal metrics.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import sys
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from sqlalchemy import create_engine, delete, select
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session, sessionmaker

logger = logging.getLogger(__name__)

QUARTER = "2026Q1"
PROCESSING_VERSION = "v1.0.0"
BATCH_SIZE = 2000


def _ensure_backend_on_path() -> None:
    backend_path = str(Path(__file__).resolve().parents[1] / "backend")
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)


def _parse_reactions(value: str) -> List[str]:
    """Convert pipeline reactions to the JSON-list shape used by the model."""
    raw = (value or "").strip()
    if not raw:
        return []
    if raw.startswith("["):
        parsed = json.loads(raw)
        if not isinstance(parsed, list):
            raise ValueError("reactions JSON must be a list")
        values = parsed
    else:
        values = raw.split("|")

    result: List[str] = []
    seen = set()
    for item in values:
        reaction = str(item).strip().upper()
        if reaction and reaction not in seen:
            result.append(reaction)
            seen.add(reaction)
    return result


def _optional_float(value: str) -> Optional[float]:
    return float(value) if value and value.strip() else None


def _read_report_batches(path: Path) -> Iterable[List[Dict[str, Any]]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        batch: List[Dict[str, Any]] = []
        for row in reader:
            batch.append(
                {
                    "report_id": row["report_id"].strip(),
                    "drug_name": row["drug_name"].strip(),
                    "reactions": _parse_reactions(row.get("reactions", "")),
                    "patient_age": _optional_float(row.get("patient_age", "")),
                    "patient_sex": row.get("patient_sex", "").strip() or None,
                    "event_date": row.get("event_date", "").strip() or None,
                    "report_quarter": row.get("report_quarter", "").strip() or QUARTER,
                    "source": row.get("source", "").strip() or "FDA_FAERS",
                }
            )
            if len(batch) >= BATCH_SIZE:
                yield batch
                batch = []
        if batch:
            yield batch


def _aggregate_pair_batches(path: Path) -> Dict[Tuple[str, str, str], int]:
    counts: Dict[Tuple[str, str, str], int] = defaultdict(int)
    rows = 0
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            drug = row["drug_name"].strip()
            event = row["event_name"].strip()
            if drug and event:
                counts[(drug, event, QUARTER)] += 1
            rows += 1
            if rows % 100000 == 0:
                logger.info("Aggregated %d pair rows (%d unique keys).", rows, len(counts))
    logger.info("Aggregated %d pair rows into %d keys.", rows, len(counts))
    return counts


def _insert_batch(db: Session, table, rows: List[Dict[str, Any]], dialect: str) -> None:
    if not rows:
        return
    if dialect == "postgresql":
        insert = postgres_insert
    elif dialect == "sqlite":
        insert = sqlite_insert
    else:
        raise RuntimeError(f"Unsupported database dialect: {dialect}")

    statement = insert(table).values(rows)
    primary_key = next(iter(table.primary_key.columns)).name
    update_values = {
        column.name: statement.excluded[column.name]
        for column in table.columns
        if column.name != primary_key
    }
    db.execute(statement.on_conflict_do_update(index_elements=[primary_key], set_=update_values))


def _insert_pairs(db: Session, table, counts: Dict[Tuple[str, str, str], int], dialect: str) -> int:
    rows = [
        {"drug_name": drug, "event_name": event, "count": count, "quarter": quarter}
        for (drug, event, quarter), count in counts.items()
    ]
    for start in range(0, len(rows), BATCH_SIZE):
        _insert_batch(db, table, rows[start : start + BATCH_SIZE], dialect)
    return len(rows)


def load_report_level_faers(
    reports_path: Path,
    pairs_path: Path,
    database_url: str,
) -> Dict[str, int]:
    _ensure_backend_on_path()
    from database.models import (
        DrugEventPairModel,
        FAERSQuarterlyMetadataModel,
        ProcessedReportModel,
    )

    engine = create_engine(database_url, pool_pre_ping=True)
    if engine.dialect.name not in {"postgresql", "sqlite"}:
        raise RuntimeError(f"Unsupported database dialect: {engine.dialect.name}")
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    pair_counts = _aggregate_pair_batches(pairs_path)

    db = SessionLocal()
    reports = 0
    try:
        for batch in _read_report_batches(reports_path):
            _insert_batch(db, ProcessedReportModel.__table__, batch, engine.dialect.name)
            db.commit()
            reports += len(batch)
            if reports % 100000 < BATCH_SIZE:
                logger.info("Loaded %d processed reports.", reports)

        # The target table has only a surrogate PK, so replace this quarter's
        # aggregate rows to make reruns idempotent without schema changes.
        db.execute(delete(DrugEventPairModel).where(DrugEventPairModel.quarter == QUARTER))
        pairs = _insert_pairs(db, DrugEventPairModel.__table__, pair_counts, engine.dialect.name)

        metadata = {
            "release_id": QUARTER,
            "quarter": QUARTER,
            "dataset_release": f"FDA FAERS {QUARTER}",
            "import_date": date.today(),
            "processing_version": PROCESSING_VERSION,
            "total_reports": reports,
            "processed_at": datetime.now(timezone.utc),
        }
        metadata_insert = (
            postgres_insert(FAERSQuarterlyMetadataModel.__table__)
            if engine.dialect.name == "postgresql"
            else sqlite_insert(FAERSQuarterlyMetadataModel.__table__)
        )
        metadata_statement = metadata_insert.values(metadata)
        metadata_statement = metadata_statement.on_conflict_do_update(
            index_elements=["release_id"],
            set_={key: metadata_statement.excluded[key] for key in metadata if key != "release_id"},
        )
        db.execute(metadata_statement)
        db.commit()
        logger.info("Loaded %d reports and %d drug-event pairs.", reports, pairs)
        return {"processed_reports": reports, "drug_event_pairs": pairs}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="import-report-level-faers")
    parser.add_argument("--reports", required=True, type=Path)
    parser.add_argument("--pairs", required=True, type=Path)
    parser.add_argument("--db-url", default=os.environ.get("DATABASE_URL", ""))
    args = parser.parse_args(argv)
    if not args.db_url:
        logger.error("DATABASE_URL not set and --db-url not provided.")
        return 1

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    load_report_level_faers(args.reports, args.pairs, args.db_url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())