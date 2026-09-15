"""Tests for schema-conformant export and pipeline end-to-end determinism."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from data_pipeline.config import PipelineConfig
from data_pipeline.export import build_candidate_signals, build_normalized_reports, write_datasets, write_json
from data_pipeline.run_pipeline import run_pipeline


def _load_schema(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def test_normalized_report_schema_fields(test_config):
    pairs = pd.DataFrame(
        {
            "primaryid": ["R001", "R001", "R002", "R003"],
            "caseid": ["C001", "C001", "C002", "C003"],
            "drug_name": ["ASPIRIN", "ASPIRIN", "WARFARIN", "ASPIRIN"],
            "event_name": ["BLEEDING", "GASTROINTESTINAL BLEEDING", "HAEMORRHAGE", "BLEEDING"],
            "raw_drug_name": ["ASPIRIN", "ASPIRIN", "WARFARIN", "ASPIRIN"],
            "raw_reaction": ["Bleeding", "Gastrointestinal bleeding", "Haemorrhage", "Bleeding"],
            "source": "FDA_FAERS",
        }
    )
    cases = pd.DataFrame(
        {
            "primaryid": ["R001", "R002", "R003"],
            "caseid": ["C001", "C002", "C003"],
            "patient_age": [55.0, 62.0, 48.0],
            "patient_sex": ["F", "M", "F"],
            "event_date": ["2026-01-10", "2026-02-05", "2026-01-20"],
            "source": "FDA_FAERS",
        }
    )
    records = build_normalized_reports(pairs, cases, test_config)
    schema = _load_schema(test_config.schema_path("normalized_report"))
    import jsonschema
    for rec in records:
        jsonschema.validate(instance=rec, schema=schema)
    # reactions are all the report's unique PTs
    r001 = next(r for r in records if r["report_id"] == "R001" and r["drug_name"] == "ASPIRIN")
    assert sorted(r001["reactions"]) == ["BLEEDING", "GASTROINTESTINAL BLEEDING"]
    assert r001["source"] == "FDA_FAERS"
    assert r001["report_quarter"] == "2026Q1"


def test_candidate_signal_schema_fields(test_config):
    candidates = pd.DataFrame(
        {
            "signal_id": ["SIG-ABC1234567"],
            "drug_name": ["ASPIRIN"],
            "event_name": ["BLEEDING"],
            "supporting_report_count": [20],
            "prr": [3.5],
            "ror": [4.0],
            "trend_score": [None],
            "risk_score": [None],
            "priority_level": [None],
            "candidate_status": ["candidate"],
            "dataset_version": ["2026Q1"],
        }
    )
    schema = _load_schema(test_config.schema_path("candidate_signal"))
    records = build_candidate_signals(candidates, test_config, schema)
    import jsonschema
    for rec in records:
        jsonschema.validate(instance=rec, schema=schema)
    assert records[0]["signal_id"].startswith("SIG-")
    assert records[0]["supporting_report_count"] == 20


def test_full_pipeline_end_to_end(test_config):
    """Run the complete pipeline on synthetic data; exit cleanly; outputs exist."""

    result = run_pipeline(test_config)
    out = test_config.output_dir
    assert (out / "drug_event_pairs.csv").is_file()
    assert (out / "signal_metrics.csv").is_file()
    assert (out / "candidate_signals.csv").is_file()
    assert (out / "normalized_reports.csv").is_file()
    assert (out / "data_quality_report.json").is_file()
    assert (out / "pipeline_manifest.json").is_file()
    assert result.reconciliation["stages"]["candidates"] == result.reconciliation["signals"]
    assert result.manifest["outcome"] == "completed"

    candidate_records = json.loads((out / "candidate_signals.json").read_text(encoding="utf-8"))
    metrics = pd.read_csv(out / "signal_metrics.csv")
    assert "signal_id" in metrics.columns

    candidate_pairs = {
        (record["drug_name"], record["event_name"]): record["signal_id"]
        for record in candidate_records
    }
    metric_pairs = {
        (row.drug_name, row.event_name): row.signal_id
        for row in metrics.itertuples(index=False)
        if (row.drug_name, row.event_name) in candidate_pairs
    }
    assert metric_pairs == candidate_pairs


def test_determinism_two_runs_identical(test_config):
    """Two identical runs must produce byte-identical data artifacts."""

    result_a = run_pipeline(test_config)
    dir_a = test_config.output_dir

    test_config2 = PipelineConfig(
        quarter=test_config.quarter,
        data_dir=test_config.data_dir,
        output_dir=test_config.data_dir / "out2",
    )
    result_b = run_pipeline(test_config2)
    dir_b = test_config2.output_dir

    artifacts = [
        "drug_event_pairs.csv",
        "signal_metrics.csv",
        "candidate_signals.csv",
        "normalized_reports.csv",
        "candidate_signals.json",
        "normalized_reports.json",
        "data_quality_report.json",
    ]
    for name in artifacts:
        data_a = (dir_a / name).read_bytes()
        data_b = (dir_b / name).read_bytes()
        assert data_a == data_b, "artifact %s differs between identical runs" % name

    assert result_a.reconciliation == result_b.reconciliation