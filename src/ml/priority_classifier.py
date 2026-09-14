"""Priority Classifier — Member 2 AI/ML Layer.

Maps a risk_score (0.0–1.0) to the priority_level enum defined in
shared-schemas/signal-schema.json:

    "low" | "medium" | "high" | "critical" | null

THRESHOLDS (configurable via environment variables)
---------------------------------------------------
    >= ML_PRIORITY_CRITICAL (default 0.75) → "critical"
    >= ML_PRIORITY_HIGH     (default 0.50) → "high"
    >= ML_PRIORITY_MEDIUM   (default 0.25) → "medium"
    <  ML_PRIORITY_MEDIUM                 → "low"
    risk_score is None                    → None

Threshold rationale
-------------------
These thresholds partition the 0–1 score range into four equal-width
quartiles as a transparent starting point.  The mock frontend data
(mock-adapter.ts) shows:
    risk_score 82  → "critical"   (0.82 >= 0.75 ✓)
    risk_score 15  → "low"        (0.15 <  0.25 ✓)
which is consistent with these thresholds.

SAFETY
------
- None risk_score → None priority_level.
- Non-finite or out-of-range values → None.
- Original PRR/ROR values are never touched.
"""

from __future__ import annotations

import math
from typing import Optional

from .config import (
    PRIORITY_CRITICAL_THRESHOLD,
    PRIORITY_HIGH_THRESHOLD,
    PRIORITY_MEDIUM_THRESHOLD,
)

# Allowed enum values (must match signal-schema.json exactly)
PRIORITY_LEVELS = frozenset({"low", "medium", "high", "critical"})


def classify_priority(risk_score: Optional[float]) -> Optional[str]:
    """Map a risk_score to a priority_level enum string.

    Parameters
    ----------
    risk_score : float in [0.0, 1.0] or None.

    Returns
    -------
    "low" | "medium" | "high" | "critical" | None
    """
    if risk_score is None:
        return None
    try:
        v = float(risk_score)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(v):
        return None

    if v >= PRIORITY_CRITICAL_THRESHOLD:
        return "critical"
    if v >= PRIORITY_HIGH_THRESHOLD:
        return "high"
    if v >= PRIORITY_MEDIUM_THRESHOLD:
        return "medium"
    return "low"
