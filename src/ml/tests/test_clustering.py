"""Tests for clustering.py."""

import pytest
from ml.clustering import cluster_signals, cluster_result_to_dict


def _sig(signal_id, drug, event, prr, count, risk_score=0.5, ror=None):
    return {
        "signal_id": signal_id,
        "drug_name": drug,
        "event_name": event,
        "prr": prr,
        "ror": ror,
        "supporting_report_count": count,
        "risk_score": risk_score,
        "priority_level": "medium",
        "trend_score": None,
        "candidate_status": "candidate",
        "dataset_version": "2026Q1",
    }


SIGNALS = [
    _sig("s1", "ASPIRIN",    "BLEEDING",    8.4, 312, 0.62),
    _sig("s2", "ASPIRIN",    "TINNITUS",    3.1,  45, 0.28),
    _sig("s3", "WARFARIN",   "BLEEDING",    6.8, 287, 0.58),
    _sig("s4", "METFORMIN",  "LACTIC ACIDOSIS", 5.2, 48, 0.41),
    _sig("s5", "IBUPROFEN",  "BLEEDING",    4.3, 193, 0.37),
    _sig("s6", "IBUPROFEN",  "RENAL INJURY", 3.9,  88, 0.31),
]


# ---------------------------------------------------------------------------
# Drug-centric grouping
# ---------------------------------------------------------------------------

def test_drug_cluster_groups_correctly():
    result = cluster_signals(SIGNALS)
    assert "ASPIRIN" in result.drug_clusters
    assert set(result.drug_clusters["ASPIRIN"]) == {"s1", "s2"}


def test_drug_cluster_ibuprofen():
    result = cluster_signals(SIGNALS)
    assert set(result.drug_clusters["IBUPROFEN"]) == {"s5", "s6"}


def test_drug_cluster_single_signal():
    result = cluster_signals(SIGNALS)
    assert result.drug_clusters["METFORMIN"] == ["s4"]


# ---------------------------------------------------------------------------
# Event-centric grouping
# ---------------------------------------------------------------------------

def test_event_cluster_bleeding():
    result = cluster_signals(SIGNALS)
    assert set(result.event_clusters["BLEEDING"]) == {"s1", "s3", "s5"}


def test_event_cluster_single():
    result = cluster_signals(SIGNALS)
    assert result.event_clusters["LACTIC ACIDOSIS"] == ["s4"]


# ---------------------------------------------------------------------------
# Feature-based clustering
# ---------------------------------------------------------------------------

def test_feature_clusters_run_without_error():
    result = cluster_signals(SIGNALS, n_feature_clusters=2)
    if result.feature_clustering_available:
        assert result.feature_clustering_n_clusters >= 1
        total_in_clusters = sum(fc.size for fc in result.feature_clusters)
        assert total_in_clusters == len(SIGNALS)


def test_feature_cluster_centroids_are_finite():
    result = cluster_signals(SIGNALS)
    import math
    for fc in result.feature_clusters:
        if fc.centroid_prr is not None:
            assert math.isfinite(fc.centroid_prr)
        if fc.centroid_risk_score is not None:
            assert math.isfinite(fc.centroid_risk_score)


def test_feature_cluster_description_no_medical_claims():
    result = cluster_signals(SIGNALS)
    forbidden = ["causes", "unsafe", "causality", "proven", "confirmed"]
    for fc in result.feature_clusters:
        for word in forbidden:
            assert word not in fc.description.lower()


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_empty_signals():
    result = cluster_signals([])
    assert result.total_signals == 0
    assert result.drug_clusters == {}
    assert result.event_clusters == {}
    assert result.feature_clusters == []


def test_single_signal():
    result = cluster_signals([SIGNALS[0]])
    assert result.total_signals == 1
    assert len(result.drug_clusters) == 1


def test_deterministic():
    r1 = cluster_signals(SIGNALS)
    r2 = cluster_signals(SIGNALS)
    assert r1.drug_clusters == r2.drug_clusters
    assert r1.event_clusters == r2.event_clusters


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------

def test_cluster_result_to_dict():
    result = cluster_signals(SIGNALS)
    d = cluster_result_to_dict(result)
    assert "drug_clusters" in d
    assert "event_clusters" in d
    assert "feature_clusters" in d
    assert "disclaimer" in d
    assert "total_signals" in d
    assert d["total_signals"] == len(SIGNALS)


def test_disclaimer_present():
    result = cluster_signals(SIGNALS)
    assert len(result.disclaimer) > 0
    assert "review" in result.disclaimer.lower()
