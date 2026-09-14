"""Trend Scorer — Member 2 AI/ML Layer.

Computes a reporting-trend indicator for each candidate signal.

IMPORTANT INTERPRETATION NOTE
------------------------------
trend_score measures changes in FAERS *reporting behaviour*, not changes
in actual disease incidence or drug safety.  An upward trend means more
spontaneous reports were submitted; it does NOT mean the drug caused more
adverse events.

OUTPUT
------
trend_score : float in [-1.0, 1.0] or None

    +1.0 : strong upward reporting trend (accelerating reports)
     0.0 : stable reporting
    -1.0 : strong downward reporting trend (declining reports)
    None : insufficient temporal data (single quarter or no date info)

ALGORITHM
---------
If signal_metrics contains trend_data (list of {"quarter": str, "count": int}
with >= 2 data points), a simple slope-based trend is computed:

  1. Sort data points by quarter string (lexicographic, works for YYYYQn).
  2. Fit a linear regression over the normalised index (0..n-1) vs count.
  3. Normalise the slope against the mean count to get a relative change rate.
  4. Clamp to [-1.0, 1.0].

If only one quarter exists or trend_data is absent, trend_score = None and
SINGLE_QUARTER_EXPLANATION is recorded.

SINGLE-QUARTER FALLBACK
-----------------------
The 2026Q1 dataset contains only one quarter.  In this case trend_score is
intentionally set to None.  This is the correct behaviour per the spec:
    "Trend unavailable because only one dataset quarter is available."
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

# Human-readable explanation attached to None trend scores.
SINGLE_QUARTER_EXPLANATION = (
    "Trend score unavailable: only one dataset quarter is present in the "
    "input data.  A longitudinal trend requires reports from at least two "
    "consecutive quarters."
)


def _parse_trend_data(trend_data: Any) -> Optional[List[Dict[str, Any]]]:
    """Validate and return trend_data list or None."""
    if not isinstance(trend_data, list) or len(trend_data) < 2:
        return None
    validated = []
    for entry in trend_data:
        if not isinstance(entry, dict):
            return None
        q = entry.get("quarter")
        c = entry.get("count")
        if not isinstance(q, str) or c is None:
            return None
        try:
            count = float(c)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(count) or count < 0:
            return None
        validated.append({"quarter": q, "count": count})
    return validated if len(validated) >= 2 else None


def _linear_slope(xs: List[float], ys: List[float]) -> float:
    """Return OLS slope for paired lists xs, ys."""
    n = len(xs)
    if n < 2:
        return 0.0
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den = sum((x - mean_x) ** 2 for x in xs)
    return num / den if den != 0 else 0.0


def compute_trend_score(
    trend_data: Optional[List[Dict[str, Any]]] = None,
) -> Optional[float]:
    """Compute a normalised reporting-trend score.

    Parameters
    ----------
    trend_data : list of {"quarter": str, "count": int/float} dicts,
                 as stored in signal_metrics.trend_data.
                 Requires >= 2 data points to compute a meaningful trend.

    Returns
    -------
    float in [-1.0, 1.0] or None.
    """
    points = _parse_trend_data(trend_data)
    if points is None:
        return None

    sorted_points = sorted(points, key=lambda p: p["quarter"])
    xs = list(range(len(sorted_points)))
    ys = [p["count"] for p in sorted_points]

    mean_y = sum(ys) / len(ys)
    if mean_y <= 0:
        return None

    slope = _linear_slope(xs, ys)

    # Relative slope: slope per period as a fraction of mean count.
    # Clamp to [-1.0, 1.0].
    relative = slope / mean_y
    clamped = max(-1.0, min(1.0, relative))
    return round(clamped, 6)
