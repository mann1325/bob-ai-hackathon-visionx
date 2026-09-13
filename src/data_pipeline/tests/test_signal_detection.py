"""Tests for deterministic candidate signal detection."""

from __future__ import annotations

import pandas as pd
import pytest

from data_pipeline.config import PipelineConfig
from data_pipeline.signal_detection import deterministic_signal_id, detect_signals


def _metrics(**overrides):
    return pd.DataFrame(
        {
            "drug_name": ["ASPIRIN", "ASPIRIN", "WARFARIN"],
            "event_name": ["PRR_GOOD", "LOW_COUNT", "LOW_PRR"],
            "a": [20, 2, 15],
            "prr": [3.5, 4.0, 1.2],
            "ror": [4.0, 5.0, 0.9],
            "chi_square": [12.0, 50.0, 0.1],
        }
    )


def test_default_thresholds_select_only_first():
    cfg = PipelineConfig(quarter="2026Q1")
    cand, stats = detect_signals(_metrics(), cfg)
    # ASPIRIN/PRR_GOOD: a=20>=3 prr=3.5>=2 chi2=12>=4 -> candidate
    assert len(cand) == 1
    assert cand.iloc[0]["drug_name"] == "ASPIRIN"
    assert cand.iloc[0]["event_name"] == "PRR_GOOD"
    assert cand.iloc[0]["candidate_status"] == "candidate"
    assert cand.iloc[0]["supporting_report_count"] == 20
    assert cand.iloc[0]["dataset_version"] == "2026Q1"
    assert stats.candidates_detected == 1
    # No prohibited AI fields should be set beyond schema placeholders.
    assert cand.iloc[0]["risk_score"] is None
    assert cand.iloc[0]["priority_level"] is None
    assert cand.iloc[0]["trend_score"] is None


def test_thresholds_configurable():
    cfg = PipelineConfig(quarter="2026Q1", min_supporting_reports=15, min_prr=1.0, min_chi_square=0.0)
    cand, stats = detect_signals(_metrics(), cfg)
    # WARFARIN/LOW_PRR also qualifies now (a=15, prr=1.2)
    assert set(cand["drug_name"]) == {"ASPIRIN", "WARFARIN"}
    assert stats.candidates_detected == 2


def test_deterministic_signal_id_stable():
    cfg = PipelineConfig(quarter="2026Q1")
    cand1, _ = detect_signals(_metrics(), cfg)
    cand2, _ = detect_signals(_metrics(), cfg)
    assert cand1.equals(cand2)
    # ids stable across quarters (same schema)
    id_a = deterministic_signal_id("ASPIRIN", "PRR_GOOD")
    id_b = deterministic_signal_id("ASPIRIN", "PRR_GOOD")
    id_diff = deterministic_signal_id("ASPIRIN", "OTHER")
    assert id_a == id_b
    assert id_a != id_diff
    assert id_a.startswith("SIG-")
    assert len(id_a) == 4 + 10


def test_nan_prr_excluded():
    df = pd.DataFrame(
        {
            "drug_name": ["X"],
            "event_name": ["Y"],
            "a": [10],
            "prr": [float("nan")],
            "ror": [None],
            "chi_square": [10.0],
        }
    )
    cfg = PipelineConfig(quarter="2026Q1")
    cand, stats = detect_signals(df, cfg)
    assert len(cand) == 0
    assert stats.candidates_detected == 0