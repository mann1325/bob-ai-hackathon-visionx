"""Tests for trend_scorer.py."""

import pytest
from ml.trend_scorer import compute_trend_score, SINGLE_QUARTER_EXPLANATION


# ---------------------------------------------------------------------------
# Single-quarter / no data → None
# ---------------------------------------------------------------------------

def test_none_trend_data_returns_none():
    assert compute_trend_score(None) is None


def test_empty_list_returns_none():
    assert compute_trend_score([]) is None


def test_single_point_returns_none():
    assert compute_trend_score([{"quarter": "2026Q1", "count": 100}]) is None


# ---------------------------------------------------------------------------
# Multi-quarter trends
# ---------------------------------------------------------------------------

def test_increasing_trend_positive():
    data = [
        {"quarter": "2025Q1", "count": 10},
        {"quarter": "2025Q2", "count": 20},
        {"quarter": "2025Q3", "count": 30},
        {"quarter": "2025Q4", "count": 40},
    ]
    score = compute_trend_score(data)
    assert score is not None
    assert score > 0.0


def test_decreasing_trend_negative():
    data = [
        {"quarter": "2025Q1", "count": 40},
        {"quarter": "2025Q2", "count": 30},
        {"quarter": "2025Q3", "count": 20},
        {"quarter": "2025Q4", "count": 10},
    ]
    score = compute_trend_score(data)
    assert score is not None
    assert score < 0.0


def test_stable_trend_near_zero():
    data = [
        {"quarter": "2025Q1", "count": 100},
        {"quarter": "2025Q2", "count": 100},
        {"quarter": "2025Q3", "count": 100},
    ]
    score = compute_trend_score(data)
    assert score is not None
    assert abs(score) < 0.01


def test_two_points_works():
    data = [
        {"quarter": "2025Q1", "count": 10},
        {"quarter": "2025Q2", "count": 20},
    ]
    score = compute_trend_score(data)
    assert score is not None
    assert score > 0.0


# ---------------------------------------------------------------------------
# Score bounds
# ---------------------------------------------------------------------------

def test_score_clamped_to_negative_one():
    data = [
        {"quarter": "2025Q1", "count": 1000},
        {"quarter": "2025Q2", "count": 1},
    ]
    score = compute_trend_score(data)
    assert score is not None
    assert score >= -1.0


def test_score_clamped_to_positive_one():
    data = [
        {"quarter": "2025Q1", "count": 1},
        {"quarter": "2025Q2", "count": 1000},
    ]
    score = compute_trend_score(data)
    assert score is not None
    assert score <= 1.0


# ---------------------------------------------------------------------------
# Invalid data handling
# ---------------------------------------------------------------------------

def test_invalid_entry_type_returns_none():
    assert compute_trend_score(["not_a_dict"]) is None


def test_missing_count_key_returns_none():
    data = [{"quarter": "2025Q1"}, {"quarter": "2025Q2"}]
    assert compute_trend_score(data) is None


def test_negative_count_returns_none():
    data = [
        {"quarter": "2025Q1", "count": -10},
        {"quarter": "2025Q2", "count": 20},
    ]
    assert compute_trend_score(data) is None


def test_deterministic():
    data = [
        {"quarter": "2025Q1", "count": 10},
        {"quarter": "2025Q2", "count": 25},
        {"quarter": "2025Q3", "count": 40},
    ]
    assert compute_trend_score(data) == compute_trend_score(data)
