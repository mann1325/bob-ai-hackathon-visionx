"""Signal Clustering — Member 2 AI/ML Layer (Optional/Stretch).

Groups candidate signals by observed statistical and reporting characteristics
to surface patterns that may deserve collective investigation attention.

WHAT A CLUSTER MEANS
---------------------
A cluster groups signals with similar observed reporting characteristics.
It does NOT mean:
  - Same biological mechanism
  - Same causality
  - Same clinical risk
  - Shared regulatory action required

Clusters are pattern-discovery aids for human reviewers, not decisions.

CLUSTERING STRATEGIES
---------------------
Two complementary groupings are provided:

1. DRUG-CENTRIC  (same drug, multiple events)
   Groups all events reported for the same drug.
   Useful for: "Does ASPIRIN have a cluster of haematological signals?"

2. EVENT-CENTRIC  (same event, multiple drugs)
   Groups all drugs reported for the same event.
   Useful for: "Is HAEMORRHAGE appearing across many drug classes?"

3. FEATURE-BASED  (statistical similarity via KMeans)
   Clusters signals by numerical features: prr, ror, supporting_report_count,
   risk_score. Reveals signals with similar statistical fingerprints regardless
   of drug/event identity.
   Requires sklearn (optional dependency — gracefully skipped if absent).

OUTPUT
------
ClusterResult contains three fields:
  drug_clusters  : dict mapping drug_name → list of signal_ids
  event_clusters : dict mapping event_name → list of signal_ids
  feature_clusters: list of FeatureCluster objects (if sklearn available)

SAFETY
------
- Cluster labels are purely descriptive, not regulatory conclusions.
- Original PRR/ROR/counts are never modified.
- If sklearn is unavailable, feature clustering is skipped gracefully.
"""

from __future__ import annotations

import math
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class FeatureCluster:
    """One feature-based cluster of signals."""
    cluster_id: int
    signal_ids: List[str]
    size: int
    centroid_prr: Optional[float]
    centroid_ror: Optional[float]
    centroid_risk_score: Optional[float]
    centroid_report_count: Optional[float]
    description: str  # human-readable summary, NOT a medical conclusion


@dataclass
class ClusterResult:
    """Complete clustering output for a set of enriched signals."""
    total_signals: int
    drug_clusters: Dict[str, List[str]]    # drug_name → [signal_id, ...]
    event_clusters: Dict[str, List[str]]   # event_name → [signal_id, ...]
    feature_clusters: List[FeatureCluster] = field(default_factory=list)
    feature_clustering_available: bool = False
    feature_clustering_n_clusters: int = 0
    disclaimer: str = (
        "Clusters reflect signals with similar observed reporting characteristics. "
        "They do not imply shared biological mechanism, causality, or clinical equivalence. "
        "All cluster findings require qualified pharmacovigilance professional review."
    )


# ---------------------------------------------------------------------------
# Drug-centric and event-centric grouping (no external dependencies)
# ---------------------------------------------------------------------------

def _group_by_drug(signals: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """Group signal_ids by drug_name."""
    groups: Dict[str, List[str]] = {}
    for s in signals:
        drug = s.get("drug_name") or "UNKNOWN"
        sid = s.get("signal_id") or ""
        groups.setdefault(drug, []).append(sid)
    # Sort signal lists for determinism
    return {k: sorted(v) for k, v in sorted(groups.items())}


def _group_by_event(signals: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """Group signal_ids by event_name."""
    groups: Dict[str, List[str]] = {}
    for s in signals:
        event = s.get("event_name") or "UNKNOWN"
        sid = s.get("signal_id") or ""
        groups.setdefault(event, []).append(sid)
    return {k: sorted(v) for k, v in sorted(groups.items())}


# ---------------------------------------------------------------------------
# Feature-based clustering (KMeans via sklearn — optional)
# ---------------------------------------------------------------------------

def _safe_float(v) -> Optional[float]:
    if v is None:
        return None
    try:
        f = float(v)
        return f if math.isfinite(f) else None
    except (TypeError, ValueError):
        return None


def _build_feature_matrix(signals: List[Dict[str, Any]]):
    """Build a (n_signals, 4) numpy matrix of normalised features.

    Features: prr, ror, log1p(supporting_report_count), risk_score
    Missing values are imputed with the column median (conservative).
    """
    import numpy as np

    rows = []
    for s in signals:
        prr = _safe_float(s.get("prr")) or 0.0
        ror = _safe_float(s.get("ror")) or prr      # fallback to PRR if ROR missing
        count = _safe_float(s.get("supporting_report_count")) or 0.0
        risk = _safe_float(s.get("risk_score")) or 0.0
        rows.append([prr, ror, math.log1p(count), risk])

    X = np.array(rows, dtype=float)

    # Column-wise min-max normalisation to [0, 1]
    col_min = X.min(axis=0)
    col_max = X.max(axis=0)
    col_range = col_max - col_min
    # Avoid divide-by-zero for constant columns
    col_range[col_range == 0] = 1.0
    X_norm = (X - col_min) / col_range
    return X_norm, rows


def _determine_n_clusters(n_signals: int, requested: Optional[int]) -> int:
    """Choose a sensible number of clusters."""
    if requested is not None and requested > 0:
        return min(requested, n_signals)
    # Heuristic: sqrt(n/2), clamped to [2, 8]
    heuristic = max(2, min(8, int(math.sqrt(n_signals / 2))))
    return heuristic


def _feature_cluster(
    signals: List[Dict[str, Any]],
    n_clusters: Optional[int] = None,
    random_state: int = 42,
) -> List[FeatureCluster]:
    """Run KMeans feature clustering. Returns empty list if sklearn unavailable."""
    try:
        from sklearn.cluster import KMeans
        import numpy as np
    except ImportError:
        logger.warning("scikit-learn not installed — feature clustering skipped.")
        return []

    if len(signals) < 2:
        return []

    k = _determine_n_clusters(len(signals), n_clusters)
    X_norm, raw_rows = _build_feature_matrix(signals)

    km = KMeans(n_clusters=k, random_state=random_state, n_init=10)
    labels = km.fit_predict(X_norm)

    clusters: List[FeatureCluster] = []
    for cid in range(k):
        indices = [i for i, lbl in enumerate(labels) if lbl == cid]
        if not indices:
            continue
        sids = sorted(signals[i].get("signal_id", "") for i in indices)
        prr_vals = [raw_rows[i][0] for i in indices]
        ror_vals = [raw_rows[i][1] for i in indices]
        count_vals = [raw_rows[i][2] for i in indices]  # log1p counts
        risk_vals = [raw_rows[i][3] for i in indices]

        def mean(xs): return sum(xs) / len(xs) if xs else None

        c_prr = round(mean(prr_vals), 3) if prr_vals else None
        c_ror = round(mean(ror_vals), 3) if ror_vals else None
        c_risk = round(mean(risk_vals), 3) if risk_vals else None
        c_count = round(math.expm1(mean(count_vals)), 1) if count_vals else None

        # Build a plain-language description — NO medical conclusions
        desc = (
            f"Cluster {cid + 1} of {k}: {len(sids)} signal(s) with "
            f"mean PRR {c_prr}, mean risk score {c_risk}. "
            f"Signals share similar statistical reporting characteristics. "
            f"Requires human pharmacovigilance review."
        )
        clusters.append(FeatureCluster(
            cluster_id=cid,
            signal_ids=sids,
            size=len(sids),
            centroid_prr=c_prr,
            centroid_ror=c_ror,
            centroid_risk_score=c_risk,
            centroid_report_count=c_count,
            description=desc,
        ))

    return sorted(clusters, key=lambda c: c.cluster_id)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def cluster_signals(
    signals: List[Dict[str, Any]],
    n_feature_clusters: Optional[int] = None,
) -> ClusterResult:
    """Cluster enriched signals using all available strategies.

    Parameters
    ----------
    signals : list of enriched signal dicts (from enrich_pipeline output).
    n_feature_clusters : number of KMeans clusters (auto if None).

    Returns
    -------
    ClusterResult with drug_clusters, event_clusters, feature_clusters.
    """
    if not signals:
        return ClusterResult(
            total_signals=0,
            drug_clusters={},
            event_clusters={},
        )

    drug_clusters = _group_by_drug(signals)
    event_clusters = _group_by_event(signals)
    feature_clusters = _feature_cluster(signals, n_clusters=n_feature_clusters)

    sklearn_available = False
    try:
        import sklearn  # noqa: F401
        sklearn_available = True
    except ImportError:
        pass

    return ClusterResult(
        total_signals=len(signals),
        drug_clusters=drug_clusters,
        event_clusters=event_clusters,
        feature_clusters=feature_clusters,
        feature_clustering_available=sklearn_available,
        feature_clustering_n_clusters=len(feature_clusters),
    )


def cluster_result_to_dict(result: ClusterResult) -> dict:
    """Serialise ClusterResult to a plain dict for JSON export."""
    return {
        "total_signals": result.total_signals,
        "disclaimer": result.disclaimer,
        "drug_clusters": result.drug_clusters,
        "event_clusters": result.event_clusters,
        "feature_clustering_available": result.feature_clustering_available,
        "feature_clustering_n_clusters": result.feature_clustering_n_clusters,
        "feature_clusters": [
            {
                "cluster_id": fc.cluster_id,
                "size": fc.size,
                "signal_ids": fc.signal_ids,
                "centroid_prr": fc.centroid_prr,
                "centroid_ror": fc.centroid_ror,
                "centroid_risk_score": fc.centroid_risk_score,
                "centroid_report_count": fc.centroid_report_count,
                "description": fc.description,
            }
            for fc in result.feature_clusters
        ],
    }
