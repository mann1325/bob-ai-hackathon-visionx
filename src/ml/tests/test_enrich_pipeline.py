"""Integration tests for enrich_pipeline.py."""

import json
import math
import tempfile
from pathlib import Path

import pytest

from ml.enrich_pipeline import (
    enrich_signals,
    load_candidate_signals,
    validate_against_schema,
    _strip_extra_for_validation,
)


SCHEMA_PATH = Path(__file__).resolve().parents[4] / (
    "SignalTrace_Team_Roles_and_Schemas/shared-schemas/signal-schema.json"
)

MINIMAL_SIGNAL = {
    "signal_id": "SIG-TEST001",
    "drug_name": "TESTDRUG",
    "event_name": "TESTEVENT",
    "supporting_report_count": 50,
    "prr": 3.5,
    "ror": 2.8,
    "trend_score": None,
    "risk_score": None,
    "priority_level": None,
    "candidate_status": "candidate",
    "dataset_version": "2026Q1",
}


def _write_json(data, path: Path):
    with path.open("w") as fh:
        json.dump(data, fh)


# ---------------------------------------------------------------------------
# enrich_signals
# ---------------------------------------------------------------------------

def test_enrich_populates_risk_score():
    enriched = enrich_signals([dict(MINIMAL_SIGNAL)], metrics_map={})
    assert enriched[0]["risk_score"] is not None


def test_enrich_populates_priority_level():
    enriched = enrich_signals([dict(MINIMAL_SIGNAL)], metrics_map={})
    assert enriched[0]["priority_level"] in {"low", "medium", "high", "critical"}


def test_enrich_trend_none_no_metrics():
    enriched = enrich_signals([dict(MINIMAL_SIGNAL)], metrics_map={})
    assert enriched[0]["trend_score"] is None


def test_enrich_does_not_modify_prr():
    sig = dict(MINIMAL_SIGNAL)
    original_prr = sig["prr"]
    enriched = enrich_signals([sig], metrics_map={})
    assert enriched[0]["prr"] == original_prr


def test_enrich_does_not_modify_ror():
    sig = dict(MINIMAL_SIGNAL)
    original_ror = sig["ror"]
    enriched = enrich_signals([sig], metrics_map={})
    assert enriched[0]["ror"] == original_ror


def test_enrich_does_not_modify_count():
    sig = dict(MINIMAL_SIGNAL)
    original_count = sig["supporting_report_count"]
    enriched = enrich_signals([sig], metrics_map={})
    assert enriched[0]["supporting_report_count"] == original_count


def test_enrich_with_metrics_uses_chi_square():
    metrics_map = {
        "SIG-TEST001": {
            "chi_square": 55.0,
            "prr_lower": 2.8,
            "ror_lower": 2.0,
            "trend_data": None,
        }
    }
    enriched_with = enrich_signals([dict(MINIMAL_SIGNAL)], metrics_map=metrics_map)
    enriched_without = enrich_signals([dict(MINIMAL_SIGNAL)], metrics_map={})
    # Having chi_square should increase score
    assert enriched_with[0]["risk_score"] >= enriched_without[0]["risk_score"]


def test_enrich_with_trend_data():
    metrics_map = {
        "SIG-TEST001": {
            "chi_square": None,
            "trend_data": [
                {"quarter": "2025Q3", "count": 10},
                {"quarter": "2025Q4", "count": 20},
                {"quarter": "2026Q1", "count": 30},
            ],
        }
    }
    enriched = enrich_signals([dict(MINIMAL_SIGNAL)], metrics_map=metrics_map)
    assert enriched[0]["trend_score"] is not None
    assert enriched[0]["trend_score"] > 0


# ---------------------------------------------------------------------------
# load_candidate_signals
# ---------------------------------------------------------------------------

def test_load_candidate_signals_valid():
    signals = [MINIMAL_SIGNAL]
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
        json.dump(signals, f)
        path = Path(f.name)
    loaded = load_candidate_signals(path)
    assert len(loaded) == 1
    assert loaded[0]["signal_id"] == "SIG-TEST001"


def test_load_candidate_signals_not_array_raises():
    with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
        json.dump({"not": "array"}, f)
        path = Path(f.name)
    with pytest.raises(ValueError, match="JSON array"):
        load_candidate_signals(path)


# ---------------------------------------------------------------------------
# Schema validation (only if jsonschema and schema file are available)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not SCHEMA_PATH.exists(), reason="Schema file not found")
def test_validate_enriched_signal_passes():
    sig = dict(MINIMAL_SIGNAL)
    sig["risk_score"] = 0.65
    sig["priority_level"] = "high"
    sig["trend_score"] = None
    # strip rank (not in schema)
    stripped = _strip_extra_for_validation(sig)
    validate_against_schema([stripped], SCHEMA_PATH)


@pytest.mark.skipif(not SCHEMA_PATH.exists(), reason="Schema file not found")
def test_invalid_priority_fails_schema():
    sig = dict(MINIMAL_SIGNAL)
    sig["priority_level"] = "INVALID_VALUE"
    with pytest.raises(ValueError):
        validate_against_schema([sig], SCHEMA_PATH)
