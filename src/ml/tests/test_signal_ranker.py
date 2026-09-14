"""Tests for signal_ranker.py."""

import pytest
from ml.signal_ranker import assign_ranks


def _sig(signal_id, risk_score, trend_score=None, count=10,
         drug="DRUG", event="EVENT", version="2026Q1"):
    return {
        "signal_id": signal_id,
        "drug_name": drug,
        "event_name": event,
        "supporting_report_count": count,
        "prr": 3.0,
        "ror": None,
        "risk_score": risk_score,
        "trend_score": trend_score,
        "priority_level": None,
        "candidate_status": "candidate",
        "dataset_version": version,
    }


# ---------------------------------------------------------------------------
# Correct ordering
# ---------------------------------------------------------------------------

def test_highest_risk_gets_rank_one():
    signals = [
        _sig("s1", risk_score=0.3),
        _sig("s2", risk_score=0.9),
        _sig("s3", risk_score=0.6),
    ]
    ranked = assign_ranks(signals)
    by_id = {r["signal_id"]: r["rank"] for r in ranked}
    assert by_id["s2"] == 1
    assert by_id["s3"] == 2
    assert by_id["s1"] == 3


def test_none_risk_score_ranked_last():
    signals = [
        _sig("s1", risk_score=None),
        _sig("s2", risk_score=0.5),
    ]
    ranked = assign_ranks(signals)
    by_id = {r["signal_id"]: r["rank"] for r in ranked}
    assert by_id["s2"] == 1
    assert by_id["s1"] == 2


# ---------------------------------------------------------------------------
# Tie-breaking
# ---------------------------------------------------------------------------

def test_tie_broken_by_trend_score():
    signals = [
        _sig("s1", risk_score=0.5, trend_score=0.2),
        _sig("s2", risk_score=0.5, trend_score=0.8),
    ]
    ranked = assign_ranks(signals)
    by_id = {r["signal_id"]: r["rank"] for r in ranked}
    assert by_id["s2"] == 1
    assert by_id["s1"] == 2


def test_tie_broken_by_count():
    signals = [
        _sig("s1", risk_score=0.5, trend_score=None, count=10),
        _sig("s2", risk_score=0.5, trend_score=None, count=100),
    ]
    ranked = assign_ranks(signals)
    by_id = {r["signal_id"]: r["rank"] for r in ranked}
    assert by_id["s2"] == 1


def test_tie_broken_by_drug_then_event_alphabetically():
    signals = [
        _sig("s1", risk_score=0.5, drug="ZOLPIDEM", event="AMNESIA", count=50),
        _sig("s2", risk_score=0.5, drug="ASPIRIN", event="AMNESIA", count=50),
    ]
    ranked = assign_ranks(signals)
    by_id = {r["signal_id"]: r["rank"] for r in ranked}
    # ASPIRIN < ZOLPIDEM alphabetically → s2 ranked higher
    assert by_id["s2"] == 1
    assert by_id["s1"] == 2


# ---------------------------------------------------------------------------
# Dataset-version scoping
# ---------------------------------------------------------------------------

def test_ranks_independent_per_version():
    signals = [
        _sig("s1", risk_score=0.9, version="2026Q1"),
        _sig("s2", risk_score=0.3, version="2026Q1"),
        _sig("s3", risk_score=0.1, version="2025Q4"),
        _sig("s4", risk_score=0.7, version="2025Q4"),
    ]
    ranked = assign_ranks(signals)
    by_id = {r["signal_id"]: r["rank"] for r in ranked}
    # Within 2026Q1: s1=1, s2=2
    assert by_id["s1"] == 1
    assert by_id["s2"] == 2
    # Within 2025Q4: s4=1, s3=2
    assert by_id["s4"] == 1
    assert by_id["s3"] == 2


# ---------------------------------------------------------------------------
# Deterministic
# ---------------------------------------------------------------------------

def test_deterministic():
    signals = [
        _sig("s1", risk_score=0.4),
        _sig("s2", risk_score=0.8),
        _sig("s3", risk_score=0.6),
    ]
    assert assign_ranks(signals) == assign_ranks(signals)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_empty_list():
    assert assign_ranks([]) == []


def test_single_signal_rank_one():
    ranked = assign_ranks([_sig("s1", risk_score=0.5)])
    assert ranked[0]["rank"] == 1


def test_original_not_mutated():
    sig = _sig("s1", risk_score=0.5)
    original = dict(sig)
    assign_ranks([sig])
    # original dict should not have been mutated
    assert "rank" not in sig or sig.get("rank") == original.get("rank")
