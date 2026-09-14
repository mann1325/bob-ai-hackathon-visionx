"""Deterministic candidate signal detection from disproportionality statistics.

Signal detection applies hard statistical thresholds (all configurable) and
emits deterministic, stable signal IDs derived from a SHA-256 hash of the
drug + event pair.  The same input and configuration always yields the same
signal; ``candidate_status`` is always ``candidate`` for detected signals.

The module does NOT assign risk_score, priority_level, trend_score, or any
other field outside the statistical detection scope.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

import pandas as pd

from .config import PipelineConfig

_SIGNAL_ID_SEPARATOR = "\x1f"  # ASCII Unit Separator – never in drug/event names


def deterministic_signal_id(drug_name: str, event_name: str) -> str:
    """Deterministic, stable signal identifier.

    The signal ID is a 10-hex-char prefix of SHA-256(drug + US + event)
    regardless of dataset version, so the same drug–event pair retains its
    signal ID across quarters (useful for longitudinal tracking).
    """

    key = f"{drug_name}{_SIGNAL_ID_SEPARATOR}{event_name}"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return f"SIG-{digest[:10].upper()}"


@dataclass(frozen=True)
class DetectionStats:
    total_pairs_evaluated: int
    pairs_above_thresholds: int
    finite_prr_pairs: int
    finite_chi2_pairs: int
    finite_ror_pairs: int
    candidates_detected: int


def detect_signals(metrics: pd.DataFrame, config: PipelineConfig) -> tuple[pd.DataFrame, DetectionStats]:
    """Filter the disproportionality table for candidates meeting all thresholds."""

    total = len(metrics)

    # require finite values for the required thresholds
    finite_prr = int(metrics["prr"].notna().sum()) if "prr" in metrics.columns else 0
    finite_chi2 = int(metrics["chi_square"].notna().sum()) if "chi_square" in metrics.columns else 0
    finite_ror = int(metrics["ror"].notna().sum()) if "ror" in metrics.columns else 0

    # threshold filter
    mask = pd.Series(True, index=metrics.index)
    if "a" in metrics.columns:
        mask &= metrics["a"].astype(float) >= config.min_supporting_reports
    if "prr" in metrics.columns:
        mask &= metrics["prr"].astype(float) >= config.min_prr
    if "chi_square" in metrics.columns:
        mask &= metrics["chi_square"].astype(float) >= config.min_chi_square

    # require all key metrics to be finite
    for col in ("prr", "chi_square"):
        if col in metrics.columns:
            mask &= metrics[col].astype(float).notna()

    above = int(mask.sum())
    candidates = metrics.loc[mask].copy()

    candidates["signal_id"] = candidates.apply(
        lambda r: deterministic_signal_id(r["drug_name"], r["event_name"]),
        axis=1,
    )
    candidates["supporting_report_count"] = candidates["a"].astype(int)
    candidates["candidate_status"] = "candidate"
    candidates["trend_score"] = None
    candidates["risk_score"] = None
    candidates["priority_level"] = None
    candidates["dataset_version"] = config.quarter

    # exact schema column set for shared contract
    schema_cols = [
        "signal_id",
        "drug_name",
        "event_name",
        "supporting_report_count",
        "prr",
        "ror",
        "trend_score",
        "risk_score",
        "priority_level",
        "candidate_status",
        "dataset_version",
    ]
    for col in schema_cols:
        if col not in candidates.columns:
            candidates[col] = None
    candidates = candidates[schema_cols].sort_values(
        ["supporting_report_count", "prr", "drug_name", "event_name"],
        ascending=[False, False, True, True],
        kind="mergesort",
    ).reset_index(drop=True)

    # clean non-finite prr/ror into None for JSON serialisation
    for col in ("prr", "ror"):
        candidates[col] = candidates[col].where(
            candidates[col].notna() & pd.to_numeric(candidates[col], errors="coerce").notna(),
            other=None,
        )

    stats = DetectionStats(
        total_pairs_evaluated=total,
        pairs_above_thresholds=above,
        finite_prr_pairs=finite_prr,
        finite_chi2_pairs=finite_chi2,
        finite_ror_pairs=finite_ror,
        candidates_detected=len(candidates),
    )
    return candidates, stats