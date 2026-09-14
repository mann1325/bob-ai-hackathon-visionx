"""Signal Ranker — Member 2 AI/ML Layer.

Assigns a deterministic ordinal rank (1 = highest priority) to each
candidate signal within a dataset version.

SORTING LOGIC
-------------
Primary   : risk_score descending (None treated as -inf, ranked last)
Secondary : trend_score descending (None treated as -inf)
Tertiary  : supporting_report_count descending
Quaternary: drug_name ascending  (stable, deterministic tie-breaker)
Quinary   : event_name ascending (stable, deterministic tie-breaker)

DATASET VERSION SCOPING
-----------------------
Ranking is computed independently per dataset_version.  Signals from
different quarters are not compared to each other unless grouped under
the same version string.

Rank 1 is the signal deserving earliest human investigation.

SAFETY
------
- None risk_score → ranked last within its version group.
- Stable sort preserves input order within identical sort keys.
- Running the same input twice always produces the same ranks.
"""

from __future__ import annotations

from typing import Any, Dict, List


def _sort_key(signal: Dict[str, Any]):
    """Tuple key for deterministic descending priority sort."""
    risk = signal.get("risk_score")
    trend = signal.get("trend_score")
    count = signal.get("supporting_report_count") or 0
    drug = (signal.get("drug_name") or "").upper()
    event = (signal.get("event_name") or "").upper()

    # Negate numerics for descending sort; None → -inf (ranked last)
    risk_key = -(risk if risk is not None else float("-inf"))
    trend_key = -(trend if trend is not None else float("-inf"))
    count_key = -count

    return (risk_key, trend_key, count_key, drug, event)


def assign_ranks(signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return a new list of signals with 'rank' field populated.

    Signals are ranked within each dataset_version independently.
    Each signal dict is shallow-copied; originals are not mutated.

    Parameters
    ----------
    signals : list of signal dicts conforming to signal-schema.json.

    Returns
    -------
    List of signal dicts with 'rank' populated (1-indexed integers).
    The overall list order is preserved from the input; only 'rank' is added.
    """
    if not signals:
        return []

    # Group by dataset_version (None is treated as its own group)
    by_version: Dict[Any, List[int]] = {}
    for idx, sig in enumerate(signals):
        version = sig.get("dataset_version")
        by_version.setdefault(version, []).append(idx)

    result = [dict(s) for s in signals]  # shallow copy, preserve order

    for version, indices in by_version.items():
        # Sort indices by priority key
        sorted_indices = sorted(indices, key=lambda i: _sort_key(result[i]))
        for rank, idx in enumerate(sorted_indices, start=1):
            result[idx]["rank"] = rank

    return result
