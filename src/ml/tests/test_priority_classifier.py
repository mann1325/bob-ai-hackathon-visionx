"""Tests for priority_classifier.py."""

import pytest
from ml.priority_classifier import classify_priority


def test_none_returns_none():
    assert classify_priority(None) is None


def test_critical():
    assert classify_priority(0.75) == "critical"
    assert classify_priority(0.99) == "critical"
    assert classify_priority(1.0) == "critical"


def test_high():
    assert classify_priority(0.50) == "high"
    assert classify_priority(0.60) == "high"
    assert classify_priority(0.74) == "high"


def test_medium():
    assert classify_priority(0.25) == "medium"
    assert classify_priority(0.40) == "medium"
    assert classify_priority(0.49) == "medium"


def test_low():
    assert classify_priority(0.00) == "low"
    assert classify_priority(0.10) == "low"
    assert classify_priority(0.24) == "low"


def test_boundary_critical():
    # Exactly at threshold → critical
    assert classify_priority(0.75) == "critical"
    # Just below → high
    assert classify_priority(0.749999) == "high"


def test_boundary_high():
    assert classify_priority(0.50) == "high"
    assert classify_priority(0.499999) == "medium"


def test_boundary_medium():
    assert classify_priority(0.25) == "medium"
    assert classify_priority(0.249999) == "low"


def test_nan_returns_none():
    assert classify_priority(float("nan")) is None


def test_inf_returns_none():
    assert classify_priority(float("inf")) is None
    assert classify_priority(float("-inf")) is None


def test_valid_enum_values():
    valid = {"low", "medium", "high", "critical", None}
    for score in [0.0, 0.1, 0.25, 0.5, 0.75, 1.0]:
        assert classify_priority(score) in valid


def test_mock_adapter_alignment():
    # Frontend mock: risk_score=82 (0.82) → "critical"
    assert classify_priority(0.82) == "critical"
    # Frontend mock: risk_score=15 (0.15) → "low"
    assert classify_priority(0.15) == "low"
