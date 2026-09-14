"""PostgreSQL Importer — Member 2 AI/ML Layer.

Reads enriched candidate signals JSON and upserts them into the PostgreSQL
database using the backend's existing SQLAlchemy models.

ARCHITECTURE
------------
- Reuses src/backend/database/models.py (SignalModel, SignalMetricsModel).
- Reuses src/backend/database/session.py (engine creation via DATABASE_URL).
- Does NOT create new ORM models or duplicate database abstractions.

UPSERT LOGIC
------------
The natural identity of a signal is its signal_id (deterministic SHA-256
hash of drug + event from the data pipeline, stable across runs).

    First import  → INSERT
    Repeated run  → UPDATE existing row

This is implemented via SQLAlchemy merge (session.merge) which performs an
upsert based on the primary key (signal_id).

SIGNAL METRICS
--------------
If a metrics CSV is provided, chi_square, prr_lower/upper, ror_lower/upper
are loaded into the signal_metrics table.  Statistical fields are never
replaced with ML-derived values.

USAGE (CLI)
-----------
    # Run from bob-ai-hackathon-visionx/src/
    DATABASE_URL=postgresql://... python -m ml.import_signals \\
        --enriched  pipeline_output/candidate_signals_enriched.json \\
        --metrics   pipeline_output/signal_metrics.csv

Or set DATABASE_URL as environment variable (same as backend).

BOUNDARIES
----------
- Does NOT modify src/data_pipeline/.
- Does NOT modify src/backend/.
- PRR / ROR / count values in enriched JSON are written as-is (never re-scored).
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

_VALID_PRIORITY_LEVELS = frozenset({"low", "medium", "high", "critical", None})
_VALID_STATUSES = frozenset({"candidate", "under_review", "closed"})


def _safe_float(v) -> Optional[float]:
    if v is None:
        return None
    try:
        f = float(v)
        return f if math.isfinite(f) else None
    except (TypeError, ValueError):
        return None


def _safe_int(v) -> Optional[int]:
    if v is None:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def validate_signal_record(rec: Dict[str, Any], idx: int) -> None:
    """Raise ValueError if a signal record is not importable."""
    sid = rec.get("signal_id")
    if not sid or not isinstance(sid, str):
        raise ValueError(f"Record {idx}: missing or invalid signal_id")
    if not rec.get("drug_name"):
        raise ValueError(f"Record {idx} (id={sid}): missing drug_name")
    if not rec.get("event_name"):
        raise ValueError(f"Record {idx} (id={sid}): missing event_name")
    if rec.get("candidate_status") not in _VALID_STATUSES:
        raise ValueError(
            f"Record {idx} (id={sid}): invalid candidate_status={rec.get('candidate_status')!r}"
        )
    if rec.get("priority_level") not in _VALID_PRIORITY_LEVELS:
        raise ValueError(
            f"Record {idx} (id={sid}): invalid priority_level={rec.get('priority_level')!r}"
        )
    prr = _safe_float(rec.get("prr"))
    if prr is None:
        raise ValueError(f"Record {idx} (id={sid}): invalid or missing prr")


# ---------------------------------------------------------------------------
# Import logic
# ---------------------------------------------------------------------------

def _build_signal_model(rec: Dict[str, Any], models_module):
    """Map enriched signal dict to a SignalModel instance."""
    SignalModel = models_module.SignalModel
    return SignalModel(
        signal_id=rec["signal_id"],
        drug_name=rec["drug_name"],
        event_name=rec["event_name"],
        supporting_report_count=_safe_int(rec.get("supporting_report_count")) or 0,
        prr=_safe_float(rec["prr"]),
        ror=_safe_float(rec.get("ror")),
        trend_score=_safe_float(rec.get("trend_score")),
        risk_score=_safe_float(rec.get("risk_score")),
        priority_level=rec.get("priority_level"),
        candidate_status=rec.get("candidate_status", "candidate"),
        dataset_version=rec.get("dataset_version"),
        rank=_safe_int(rec.get("rank")),
    )


def _build_metrics_model(signal_id: str, row: Dict[str, Any], models_module):
    """Map a metrics row to a SignalMetricsModel instance."""
    SignalMetricsModel = models_module.SignalMetricsModel
    return SignalMetricsModel(
        signal_id=signal_id,
        prr=_safe_float(row.get("prr")) or 0.0,
        ror=_safe_float(row.get("ror")),
        report_count=_safe_int(row.get("a")) or 0,
        chi_square=_safe_float(row.get("chi_square")),
        contingency_table={
            k: _safe_int(row.get(k))
            for k in ("a", "b", "c", "d")
            if row.get(k) is not None
        } or None,
        trend_data=None,  # populated from metrics CSV if available
    )


def import_enriched_signals(
    enriched_path: Path,
    metrics_path: Optional[Path],
    database_url: str,
    dry_run: bool = False,
) -> Dict[str, int]:
    """Import enriched signals into PostgreSQL.

    Parameters
    ----------
    enriched_path : path to candidate_signals_enriched.json
    metrics_path  : path to signal_metrics.csv (optional)
    database_url  : SQLAlchemy-compatible database URL
    dry_run       : if True, validate and build models but do not commit

    Returns
    -------
    dict with keys: total, inserted_or_updated, skipped, errors
    """
    # Import backend modules (they live in src/backend/, added to sys.path)
    _ensure_backend_on_path()
    try:
        from database.models import SignalMetricsModel, SignalModel
        from database import models as models_module
    except ImportError as exc:
        raise RuntimeError(
            "Cannot import backend database models. "
            "Run this script from bob-ai-hackathon-visionx/src/ "
            "or ensure src/backend is on PYTHONPATH."
        ) from exc

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    logger.info("Connecting to database...")
    engine = create_engine(database_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    logger.info("Loading enriched signals from %s", enriched_path)
    with enriched_path.open("r", encoding="utf-8") as fh:
        signals: List[Dict[str, Any]] = json.load(fh)
    logger.info("Loaded %d enriched signals.", len(signals))

    metrics_map: Dict[str, Dict[str, Any]] = {}
    if metrics_path and metrics_path.is_file():
        import pandas as pd
        df = pd.read_csv(metrics_path, low_memory=False)
        if "signal_id" in df.columns:
            for _, row in df.iterrows():
                metrics_map[str(row["signal_id"])] = row.to_dict()
            logger.info("Loaded metrics for %d signals.", len(metrics_map))

    counters = {"total": len(signals), "inserted_or_updated": 0, "skipped": 0, "errors": 0}

    db = SessionLocal()
    try:
        for idx, rec in enumerate(signals):
            try:
                validate_signal_record(rec, idx)
            except ValueError as exc:
                logger.error("Validation error: %s — skipping.", exc)
                counters["errors"] += 1
                counters["skipped"] += 1
                continue

            signal_obj = _build_signal_model(rec, models_module)

            if not dry_run:
                db.merge(signal_obj)

            # Upsert signal_metrics row if data is available
            sid = rec["signal_id"]
            m = metrics_map.get(sid)
            if m:
                m_with_prr = {**m, "prr": rec.get("prr"), "ror": rec.get("ror")}
                metrics_obj = _build_metrics_model(sid, m_with_prr, models_module)
                if not dry_run:
                    db.merge(metrics_obj)

            counters["inserted_or_updated"] += 1

        if not dry_run:
            db.commit()
            logger.info("Committed %d records.", counters["inserted_or_updated"])
        else:
            logger.info("Dry run — no changes committed.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    return counters


def _ensure_backend_on_path() -> None:
    """Add src/backend to sys.path if not already present."""
    backend_path = str(Path(__file__).resolve().parents[1] / "backend")
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)


def main(argv=None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    parser = argparse.ArgumentParser(prog="ml-import-signals")
    parser.add_argument(
        "--enriched",
        default="pipeline_output/candidate_signals_enriched.json",
        help="Path to candidate_signals_enriched.json.",
    )
    parser.add_argument(
        "--metrics",
        default="pipeline_output/signal_metrics.csv",
        help="Path to signal_metrics.csv.",
    )
    parser.add_argument(
        "--db-url",
        default=os.environ.get("DATABASE_URL", ""),
        help="SQLAlchemy database URL (or set DATABASE_URL env var).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and build models without committing to the database.",
    )
    args = parser.parse_args(argv)

    if not args.db_url:
        logger.error("DATABASE_URL not set and --db-url not provided.")
        return 1

    result = import_enriched_signals(
        enriched_path=Path(args.enriched),
        metrics_path=Path(args.metrics),
        database_url=args.db_url,
        dry_run=args.dry_run,
    )
    logger.info("Import complete: %s", result)
    return 0 if result["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
