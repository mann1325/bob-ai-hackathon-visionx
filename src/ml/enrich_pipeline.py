"""Enrichment Pipeline — Member 2 AI/ML Layer.

Orchestrates the full ML enrichment workflow:

    candidate_signals.json  +  signal_metrics.csv (optional)
              ↓
    Load & join metrics
              ↓
    Risk scoring
              ↓
    Priority classification
              ↓
    Trend scoring
              ↓
    Signal ranking
              ↓
    Schema validation
              ↓
    candidate_signals_enriched.json

USAGE (CLI)
-----------
    python -m ml.enrich_pipeline \\
        --signals  pipeline_output/candidate_signals.json \\
        --metrics  pipeline_output/signal_metrics.csv \\
        --schema   SignalTrace_Team_Roles_and_Schemas/shared-schemas/signal-schema.json \\
        --out      pipeline_output/candidate_signals_enriched.json

All arguments have defaults that match the standard pipeline output layout.

BOUNDARIES
----------
- Does NOT modify src/data_pipeline/.
- Does NOT modify src/backend/.
- Does NOT alter PRR, ROR, chi_square, or supporting_report_count.
- Output conforms to signal-schema.json (additionalProperties: false).
- 'rank' is written to output but is NOT part of signal-schema.json;
  it is passed through for the DB importer only and stripped before
  schema validation if necessary (see _strip_extra_for_validation).
"""

from __future__ import annotations

import argparse
import json
import logging
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from .priority_classifier import classify_priority
from .risk_scorer import compute_risk_score
from .signal_ranker import assign_ranks
from .trend_scorer import SINGLE_QUARTER_EXPLANATION, compute_trend_score

logger = logging.getLogger(__name__)

DEFAULT_SIGNAL_SCHEMA_PATH = (
    Path(__file__).resolve().parents[1]
    / "data_pipeline"
    / "schemas"
    / "signal-schema.json"
)

# Fields that are internal to the enrichment pipeline and NOT part of the
# shared signal-schema.json (which uses additionalProperties: false).
# These are retained in the enriched JSON for the DB importer but stripped
# before schema validation.
_SCHEMA_EXTRA_FIELDS = {"rank"}

# Columns expected from signal_metrics.csv (all optional — missing → None).
_METRICS_COLS = {
    "signal_id",
    "chi_square",
    "prr_lower",
    "prr_upper",
    "ror_lower",
    "ror_upper",
    "trend_data",
}


def _safe_float(v) -> Optional[float]:
    if v is None:
        return None
    try:
        f = float(v)
        return f if math.isfinite(f) else None
    except (TypeError, ValueError):
        return None


def load_candidate_signals(path: Path) -> List[Dict[str, Any]]:
    """Load candidate signals JSON produced by the data pipeline."""
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON array in {path}, got {type(data).__name__}")
    return data


def load_signal_metrics(path: Optional[Path]) -> Dict[str, Dict[str, Any]]:
    """Load signal_metrics.csv and return a dict keyed by signal_id.

    Returns an empty dict if the file does not exist (metrics are optional).
    """
    if path is None or not path.is_file():
        logger.warning("signal_metrics.csv not found at %s — metrics unavailable.", path)
        return {}

    df = pd.read_csv(path, low_memory=False)
    if "signal_id" not in df.columns:
        logger.warning("signal_metrics.csv missing 'signal_id' column — skipping.")
        return {}

    metrics: Dict[str, Dict[str, Any]] = {}
    for _, row in df.iterrows():
        sid = str(row["signal_id"])
        metrics[sid] = {
            col: (None if pd.isna(row[col]) else row[col])
            for col in df.columns
            if col in _METRICS_COLS
        }
    return metrics


def _parse_trend_data_from_metrics(raw) -> Optional[list]:
    """Deserialise trend_data stored as a JSON string or already a list."""
    if raw is None:
        return None
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, list) else None
        except (json.JSONDecodeError, ValueError):
            return None
    return None


def enrich_signals(
    signals: List[Dict[str, Any]],
    metrics_map: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Enrich each signal with risk_score, priority_level, trend_score.

    Preserves all original fields. Does NOT modify PRR/ROR/counts.
    """
    enriched = []
    for sig in signals:
        s = dict(sig)  # shallow copy — never mutate input
        sid = s.get("signal_id", "")
        m = metrics_map.get(sid, {})

        # --- inputs (never overwrite originals) ---
        prr = _safe_float(s.get("prr"))
        ror = _safe_float(s.get("ror"))
        count = s.get("supporting_report_count")
        chi2 = _safe_float(m.get("chi_square"))
        prr_lower = _safe_float(m.get("prr_lower"))
        ror_lower = _safe_float(m.get("ror_lower"))
        trend_data_raw = _parse_trend_data_from_metrics(m.get("trend_data"))

        # --- scoring ---
        risk = compute_risk_score(
            prr=prr,
            ror=ror,
            supporting_report_count=count,
            chi_square=chi2,
            prr_lower=prr_lower,
            ror_lower=ror_lower,
        )
        priority = classify_priority(risk)
        trend = compute_trend_score(trend_data=trend_data_raw)

        s["risk_score"] = risk
        s["priority_level"] = priority
        s["trend_score"] = trend
        # rank is assigned by assign_ranks() after this step

        enriched.append(s)

    return enriched


def _strip_extra_for_validation(signal: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of signal with pipeline-internal fields removed."""
    return {k: v for k, v in signal.items() if k not in _SCHEMA_EXTRA_FIELDS}


def validate_against_schema(
    signals: List[Dict[str, Any]],
    schema_path: Path,
) -> None:
    """Validate every signal against the shared signal-schema.json.

    Raises ValueError on the first violation.
    """
    try:
        import jsonschema
    except ImportError:
        logger.warning("jsonschema not installed — skipping schema validation.")
        return

    with schema_path.open("r", encoding="utf-8") as fh:
        schema = json.load(fh)

    for idx, sig in enumerate(signals):
        stripped = _strip_extra_for_validation(sig)
        try:
            jsonschema.validate(instance=stripped, schema=schema)
        except jsonschema.ValidationError as exc:
            raise ValueError(
                f"Signal at index {idx} (id={sig.get('signal_id')}) "
                f"fails schema validation: {exc.message}"
            ) from exc


def run_enrichment(
    signals_path: Path,
    metrics_path: Optional[Path],
    schema_path: Path,
    output_path: Path,
) -> List[Dict[str, Any]]:
    """Execute the full enrichment pipeline and write output JSON.

    Returns the list of enriched signals.
    """
    logger.info("Loading candidate signals from %s", signals_path)
    signals = load_candidate_signals(signals_path)
    logger.info("Loaded %d candidate signals.", len(signals))

    logger.info("Loading signal metrics from %s", metrics_path)
    metrics_map = load_signal_metrics(metrics_path)
    logger.info("Loaded metrics for %d signals.", len(metrics_map))

    logger.info("Enriching signals (risk score, priority, trend)...")
    enriched = enrich_signals(signals, metrics_map)

    logger.info("Assigning ranks...")
    ranked = assign_ranks(enriched)

    logger.info("Validating against schema %s...", schema_path)
    validate_against_schema(ranked, schema_path)
    logger.info("Schema validation passed.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(ranked, fh, ensure_ascii=False, indent=2, sort_keys=True)
    logger.info("Enriched signals written to %s", output_path)

    counts = {
        "total": len(ranked),
        "with_risk_score": sum(1 for s in ranked if s.get("risk_score") is not None),
        "with_trend_score": sum(1 for s in ranked if s.get("trend_score") is not None),
        "priority_counts": {
            lvl: sum(1 for s in ranked if s.get("priority_level") == lvl)
            for lvl in ("critical", "high", "medium", "low", None)
        },
    }
    logger.info("Enrichment summary: %s", counts)

    return ranked


def main(argv=None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    parser = argparse.ArgumentParser(prog="ml-enrich-pipeline")
    parser.add_argument(
        "--signals",
        default="pipeline_output/candidate_signals.json",
        help="Path to candidate_signals.json from data pipeline.",
    )
    parser.add_argument(
        "--metrics",
        default="pipeline_output/signal_metrics.csv",
        help="Path to signal_metrics.csv from data pipeline.",
    )
    parser.add_argument(
        "--schema",
        default=str(DEFAULT_SIGNAL_SCHEMA_PATH),
        help="Path to shared signal-schema.json.",
    )
    parser.add_argument(
        "--out",
        default="pipeline_output/candidate_signals_enriched.json",
        help="Output path for enriched signals JSON.",
    )
    args = parser.parse_args(argv)

    run_enrichment(
        signals_path=Path(args.signals),
        metrics_path=Path(args.metrics),
        schema_path=Path(args.schema),
        output_path=Path(args.out),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
