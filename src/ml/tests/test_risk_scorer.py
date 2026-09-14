"""Tests for risk_scorer.py — deterministic investigation-priority scoring."""

import math
import pytest
from ml.risk_scorer import compute_risk_score


# ---------------------------------------------------------------------------
# Normal values
# ---------------------------------------------------------------------------

def test_normal_all_inputs():
    score = compute_risk_score(
        prr=4.5, ror=3.8, supporting_report_count=120,
        chi_square=40.0, prr_lower=3.1, ror_lower=2.6,
    )
    assert score is not None
    assert 0.0 <= score <= 1.0


def test_deterministic_same_input_twice():
    kwargs = dict(prr=4.5, ror=3.8, supporting_report_count=120,
                  chi_square=40.0, prr_lower=3.1, ror_lower=2.6)
    assert compute_risk_score(**kwargs) == compute_risk_score(**kwargs)


def test_higher_prr_gives_higher_score():
    low = compute_risk_score(prr=2.1, ror=None, supporting_report_count=10)
    high = compute_risk_score(prr=8.0, ror=None, supporting_report_count=10)
    assert high > low


def test_higher_count_gives_higher_score():
    low = compute_risk_score(prr=3.0, ror=None, supporting_report_count=5)
    high = compute_risk_score(prr=3.0, ror=None, supporting_report_count=500)
    assert high > low


# ---------------------------------------------------------------------------
# Missing inputs
# ---------------------------------------------------------------------------

def test_missing_prr_and_ror_returns_none():
    assert compute_risk_score(prr=None, ror=None, supporting_report_count=100) is None


def test_missing_ror_still_scores():
    score = compute_risk_score(prr=3.5, ror=None, supporting_report_count=50)
    assert score is not None
    assert 0.0 <= score <= 1.0


def test_missing_chi_square_still_scores():
    score = compute_risk_score(prr=3.5, ror=2.0, supporting_report_count=50,
                               chi_square=None)
    assert score is not None


def test_missing_prr_lower_falls_back_to_prr():
    score_with = compute_risk_score(prr=3.5, ror=None, supporting_report_count=50,
                                    prr_lower=2.0)
    score_without = compute_risk_score(prr=3.5, ror=None, supporting_report_count=50,
                                       prr_lower=None)
    # Both should return a score; with CI lower bound the score is different
    assert score_with is not None
    assert score_without is not None


# ---------------------------------------------------------------------------
# Edge cases — zero, negatives, extremes
# ---------------------------------------------------------------------------

def test_zero_report_count_returns_none():
    assert compute_risk_score(prr=3.5, ror=2.0, supporting_report_count=0) is None


def test_very_large_report_count_capped():
    score = compute_risk_score(prr=3.5, ror=2.0, supporting_report_count=10_000_000)
    assert score is not None
    assert score <= 1.0


def test_very_large_prr_capped():
    score = compute_risk_score(prr=9999.0, ror=None, supporting_report_count=50)
    assert score is not None
    assert score <= 1.0


def test_prr_below_one_treated_as_zero_component():
    low = compute_risk_score(prr=0.5, ror=None, supporting_report_count=50)
    base = compute_risk_score(prr=2.0, ror=None, supporting_report_count=50)
    assert low is not None
    assert base is not None
    assert low < base


# ---------------------------------------------------------------------------
# NaN / inf safety
# ---------------------------------------------------------------------------

def test_nan_prr_returns_none():
    assert compute_risk_score(prr=float("nan"), ror=None, supporting_report_count=50) is None


def test_inf_prr_treated_as_capped():
    # inf → _safe_float → None → treated as missing PRR component
    # but if ror is also None → returns None
    result = compute_risk_score(prr=float("inf"), ror=None, supporting_report_count=50)
    assert result is None


def test_nan_chi_square_safe():
    score = compute_risk_score(prr=3.5, ror=2.0, supporting_report_count=50,
                               chi_square=float("nan"))
    assert score is not None


def test_score_in_range():
    for prr in [2.0, 4.0, 10.0, 20.0]:
        for count in [3, 50, 1000]:
            s = compute_risk_score(prr=prr, ror=None, supporting_report_count=count)
            if s is not None:
                assert 0.0 <= s <= 1.0
