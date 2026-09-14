"""ML layer configuration.

All weights and thresholds are gathered here so they are:
  - Configurable via environment variables.
  - Never silently embedded in business logic.
  - Self-documenting.

RISK SCORE WEIGHTS
------------------
The risk score is a weighted combination of four normalised components.
Weights sum to 1.0.

  prr_weight       : Weight for statistical-strength component (PRR / CI lower).
  volume_weight    : Weight for evidence-volume component (log report count).
  chi2_weight      : Weight for reliability component (chi-square).
  ror_weight       : Weight for secondary-statistic component (ROR / CI lower).

Rationale (hackathon MVP):
  PRR is the primary pharmacovigilance disproportionality measure → highest
  weight. Volume (report count) provides corroboration. Chi-square formalises
  statistical reliability. ROR is a secondary corroborative measure with lower
  weight because it is highly correlated with PRR in large datasets.

PRIORITY THRESHOLDS (0.0–1.0 scale)
-------------------------------------
  critical  : >= 0.75
  high      : >= 0.50
  medium    : >= 0.25
  low       : >= 0.00

Aligned with the mock frontend data in mock-adapter.ts which maps:
  risk_score 82  → priority_level "critical"   (82/100 = 0.82 >= 0.75 ✓)
  risk_score 15  → priority_level "low"         (15/100 = 0.15 <  0.25 ✓)
"""

from __future__ import annotations

import os


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ[name])
    except (KeyError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Risk score component weights (must sum to 1.0)
# ---------------------------------------------------------------------------
RISK_WEIGHT_PRR: float = _env_float("ML_RISK_WEIGHT_PRR", 0.40)
RISK_WEIGHT_VOLUME: float = _env_float("ML_RISK_WEIGHT_VOLUME", 0.25)
RISK_WEIGHT_CHI2: float = _env_float("ML_RISK_WEIGHT_CHI2", 0.20)
RISK_WEIGHT_ROR: float = _env_float("ML_RISK_WEIGHT_ROR", 0.15)

# Saturation caps: inputs above these values are treated as the cap value
# before normalisation, preventing extreme outliers from dominating the score.
PRR_CAP: float = _env_float("ML_PRR_CAP", 20.0)         # PRR rarely meaningful beyond 20
ROR_CAP: float = _env_float("ML_ROR_CAP", 20.0)
CHI2_CAP: float = _env_float("ML_CHI2_CAP", 100.0)
LOG_COUNT_CAP: float = _env_float("ML_LOG_COUNT_CAP", 7.0)  # log(1097) ≈ 7.0

# Minimum report count to generate a non-null risk score (safety guard)
MIN_REPORTS_FOR_SCORE: int = int(_env_float("ML_MIN_REPORTS_FOR_SCORE", 1))

# ---------------------------------------------------------------------------
# Priority level thresholds (on the 0.0–1.0 risk_score scale)
# ---------------------------------------------------------------------------
PRIORITY_CRITICAL_THRESHOLD: float = _env_float("ML_PRIORITY_CRITICAL", 0.75)
PRIORITY_HIGH_THRESHOLD: float = _env_float("ML_PRIORITY_HIGH", 0.50)
PRIORITY_MEDIUM_THRESHOLD: float = _env_float("ML_PRIORITY_MEDIUM", 0.25)
# Anything below medium threshold → "low"
