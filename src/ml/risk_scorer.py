"""Risk Scorer — Member 2 AI/ML Layer.

Computes a deterministic, interpretable investigation-priority score for
every candidate signal.

OUTPUT
------
risk_score : float in [0.0, 1.0] or None
    Represents how much this signal deserves earlier or deeper human
    investigation relative to other signals in the same dataset version.

    This is NOT:
      - A probability that the drug is unsafe.
      - A probability of causality.
      - A regulatory decision or recommendation.

FORMULA
-------
Four normalised components are combined with configurable weights:

  1. PRR component   (weight: ML_RISK_WEIGHT_PRR, default 0.40)
     Uses the lower 95 % CI bound (prr_lower) when available; falls back to
     PRR itself.  The CI lower bound is more conservative and penalises noisy
     estimates with wide intervals.

  2. Volume component  (weight: ML_RISK_WEIGHT_VOLUME, default 0.25)
     log1p(supporting_report_count) normalised against a saturation cap.
     Logarithmic because FAERS report counts are highly right-skewed.

  3. Chi-square component  (weight: ML_RISK_WEIGHT_CHI2, default 0.20)
     Normalised chi-square, capped at ML_CHI2_CAP to prevent a single
     extremely significant pair from dominating.

  4. ROR component   (weight: ML_RISK_WEIGHT_ROR, default 0.15)
     Same logic as PRR component using ror_lower → ror fallback.

Each component is independently normalised to [0.0, 1.0] before weighting
so that missing values default to 0.0 contribution (not a crash).

INPUTS
------
From candidate_signals (signal-schema.json):
  prr, ror, supporting_report_count

From signal_metrics.csv (internal analytical, not schema-bound):
  chi_square, prr_lower, prr_upper, ror_lower, ror_upper

SAFETY
------
- Null, NaN, inf, negative, and zero inputs are all handled safely.
- No input is fabricated or imputed from other signals.
- Original PRR/ROR values are NEVER modified.
"""

from __future__ import annotations

import math
from typing import Optional

from .config import (
    CHI2_CAP,
    LOG_COUNT_CAP,
    MIN_REPORTS_FOR_SCORE,
    PRR_CAP,
    ROR_CAP,
    RISK_WEIGHT_CHI2,
    RISK_WEIGHT_PRR,
    RISK_WEIGHT_ROR,
    RISK_WEIGHT_VOLUME,
)


def _safe_float(value) -> Optional[float]:
    """Return a finite float or None.  Never raises."""
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) and v >= 0 else None


def _normalise(value: Optional[float], cap: float) -> float:
    """Normalise a non-negative value against a saturation cap to [0.0, 1.0].

    Missing values → 0.0 contribution (conservative: no bonus for missing data).
    """
    if value is None:
        return 0.0
    capped = min(value, cap)
    return capped / cap if cap > 0 else 0.0


def _prr_component(prr: Optional[float], prr_lower: Optional[float]) -> float:
    """Normalised PRR component using CI lower bound when available."""
    value = prr_lower if prr_lower is not None else prr
    safe = _safe_float(value)
    # PRR < 1 means under-reporting relative to background; clamp to 0
    if safe is not None and safe < 1.0:
        safe = 0.0
    return _normalise(safe, PRR_CAP)


def _ror_component(ror: Optional[float], ror_lower: Optional[float]) -> float:
    """Normalised ROR component using CI lower bound when available."""
    value = ror_lower if ror_lower is not None else ror
    safe = _safe_float(value)
    if safe is not None and safe < 1.0:
        safe = 0.0
    return _normalise(safe, ROR_CAP)


def _volume_component(count: Optional[int]) -> float:
    """Normalised log-transformed report volume component."""
    safe = _safe_float(count)
    if safe is None or safe < MIN_REPORTS_FOR_SCORE:
        return 0.0
    log_val = math.log1p(safe)
    return _normalise(log_val, LOG_COUNT_CAP)


def _chi2_component(chi2: Optional[float]) -> float:
    """Normalised chi-square reliability component."""
    safe = _safe_float(chi2)
    return _normalise(safe, CHI2_CAP)


def compute_risk_score(
    prr: Optional[float],
    ror: Optional[float],
    supporting_report_count: Optional[int],
    chi_square: Optional[float] = None,
    prr_lower: Optional[float] = None,
    ror_lower: Optional[float] = None,
) -> Optional[float]:
    """Compute a deterministic investigation-priority score.

    Parameters
    ----------
    prr : PRR value from deterministic pipeline (not modified).
    ror : ROR value from deterministic pipeline (not modified).
    supporting_report_count : raw count from deterministic pipeline.
    chi_square : from signal_metrics (optional enrichment).
    prr_lower  : PRR 95 % CI lower bound from signal_metrics (optional).
    ror_lower  : ROR 95 % CI lower bound from signal_metrics (optional).

    Returns
    -------
    float in [0.0, 1.0] or None if all core inputs are missing/invalid.
    """
    # Require at least PRR and a valid report count
    if _safe_float(prr) is None and _safe_float(ror) is None:
        return None
    count_safe = _safe_float(supporting_report_count)
    if count_safe is None or count_safe < MIN_REPORTS_FOR_SCORE:
        return None

    prr_comp = _prr_component(prr, prr_lower)
    ror_comp = _ror_component(ror, ror_lower)
    vol_comp = _volume_component(supporting_report_count)
    chi2_comp = _chi2_component(chi_square)

    score = (
        RISK_WEIGHT_PRR * prr_comp
        + RISK_WEIGHT_VOLUME * vol_comp
        + RISK_WEIGHT_CHI2 * chi2_comp
        + RISK_WEIGHT_ROR * ror_comp
    )

    # Clamp to [0.0, 1.0] as a safety guard against floating-point drift
    return round(max(0.0, min(1.0, score)), 6)
