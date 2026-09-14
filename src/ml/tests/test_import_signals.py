"""Tests for import_signals.py — validation logic (no live DB required)."""

import pytest
from ml.import_signals import validate_signal_record, _safe_float, _safe_int


VALID_RECORD = {
    "signal_id": "SIG-ABC123",
    "drug_name": "TESTDRUG",
    "event_name": "TESTEVENT",
    "supporting_report_count": 50,
    "prr": 3.5,
    "ror": 2.8,
    "risk_score": 0.65,
    "priority_level": "high",
    "trend_score": None,
    "candidate_status": "candidate",
    "dataset_version": "2026Q1",
    "rank": 1,
}


# ---------------------------------------------------------------------------
# validate_signal_record
# ---------------------------------------------------------------------------

def test_valid_record_does_not_raise():
    validate_signal_record(VALID_RECORD, 0)


def test_missing_signal_id_raises():
    rec = {**VALID_RECORD, "signal_id": ""}
    with pytest.raises(ValueError, match="signal_id"):
        validate_signal_record(rec, 0)


def test_none_signal_id_raises():
    rec = {**VALID_RECORD, "signal_id": None}
    with pytest.raises(ValueError, match="signal_id"):
        validate_signal_record(rec, 0)


def test_missing_drug_name_raises():
    rec = {**VALID_RECORD, "drug_name": ""}
    with pytest.raises(ValueError, match="drug_name"):
        validate_signal_record(rec, 0)


def test_invalid_candidate_status_raises():
    rec = {**VALID_RECORD, "candidate_status": "INVALID"}
    with pytest.raises(ValueError, match="candidate_status"):
        validate_signal_record(rec, 0)


def test_invalid_priority_level_raises():
    rec = {**VALID_RECORD, "priority_level": "urgent"}
    with pytest.raises(ValueError, match="priority_level"):
        validate_signal_record(rec, 0)


def test_null_priority_level_is_valid():
    rec = {**VALID_RECORD, "priority_level": None}
    validate_signal_record(rec, 0)  # should not raise


def test_missing_prr_raises():
    rec = {**VALID_RECORD, "prr": None}
    with pytest.raises(ValueError, match="prr"):
        validate_signal_record(rec, 0)


def test_all_valid_statuses():
    for status in ("candidate", "under_review", "closed"):
        rec = {**VALID_RECORD, "candidate_status": status}
        validate_signal_record(rec, 0)


def test_all_valid_priority_levels():
    for lvl in ("low", "medium", "high", "critical", None):
        rec = {**VALID_RECORD, "priority_level": lvl}
        validate_signal_record(rec, 0)


# ---------------------------------------------------------------------------
# _safe_float / _safe_int helpers
# ---------------------------------------------------------------------------

def test_safe_float_normal():
    assert _safe_float(3.14) == pytest.approx(3.14)


def test_safe_float_none():
    assert _safe_float(None) is None


def test_safe_float_nan():
    assert _safe_float(float("nan")) is None


def test_safe_float_inf():
    assert _safe_float(float("inf")) is None


def test_safe_int_normal():
    assert _safe_int(42) == 42


def test_safe_int_none():
    assert _safe_int(None) is None


def test_safe_int_string():
    assert _safe_int("bad") is None
