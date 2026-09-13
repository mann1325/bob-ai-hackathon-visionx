"""Tests for deterministic case/version handling."""

from __future__ import annotations

import pandas as pd
import pytest

from data_pipeline.case_processing import apply_deleted_case_filter, handle_cases, select_latest_version
from data_pipeline.config import PipelineConfig


def _demo(pairs: list) -> pd.DataFrame:
    return pd.DataFrame(pairs, columns=["primaryid", "caseid", "caseversion"])


def test_single_version_kept():
    df = _demo([("P1", "C1", "1")])
    out, stats = select_latest_version(df)
    assert len(out) == 1
    assert out.iloc[0]["primaryid"] == "P1"
    assert stats.rows_excluded == 0


def test_latest_version_selected():
    df = _demo([("P1", "C1", "1"), ("P2", "C1", "2"), ("P3", "C1", "3")])
    out, stats = select_latest_version(df)
    assert len(out) == 1
    assert out.iloc[0]["primaryid"] == "P3"
    assert stats.rows_excluded == 2
    assert stats.exclusion_reason == "duplicate caseversion rows kept"


def test_latest_version_within_quarter():
    # Same case has two versions in the same dataset; higher version wins.
    df = _demo([("Q1V1", "Q1", "1"), ("Q1V2", "Q1", "2"), ("Q2V1", "Q2", "1")])
    out, stats = select_latest_version(df)
    assert set(out["primaryid"]) == {"Q1V2", "Q2V1"}
    assert stats.rows_excluded == 1


def test_tie_break_deterministic_largest_primaryid():
    # Same caseversion twice (ambiguous) -> tie broken by largest primaryid lex.
    df = _demo([("A1", "C1", "1"), ("B2", "C1", "1")])
    out, _ = select_latest_version(df)
    assert len(out) == 1
    assert out.iloc[0]["primaryid"] == "B2"
    # Deterministic: rerun yields identical result
    out2, _ = select_latest_version(df)
    assert out.equals(out2)


def test_followup_kept_older_excluded():
    # Follow-up reports appear as higher caseversion numbers.
    df = _demo([("P0", "C10", "1"), ("P1", "C10", "2"), ("P99", "C11", "1")])
    out, stats = select_latest_version(df)
    assert set(out["primaryid"]) == {"P1", "P99"}
    assert stats.rows_excluded == 1


def test_deleted_case_filter_off_by_default():
    df = _demo([("P1", "C1", "1"), ("P2", "C2", "1")])
    cfg = PipelineConfig(quarter="2026Q1")
    out, meta = apply_deleted_case_filter(df, {"C2"}, cfg)
    assert len(out) == 2
    assert meta["rows_excluded"] == 0


def test_deleted_case_filter_on():
    df = _demo([("P1", "C1", "1"), ("P2", "C2", "1")])
    cfg = PipelineConfig(quarter="2026Q1", exclude_deleted_cases=True)
    out, meta = apply_deleted_case_filter(df, {"C2"}, cfg)
    assert len(out) == 1
    assert out.iloc[0]["caseid"] == "C1"
    assert meta["rows_excluded"] == 1


def test_handle_cases_integration():
    df = _demo([("P1", "C1", "1"), ("P2", "C1", "2"), ("P3", "C2", "1")])
    cfg = PipelineConfig(quarter="2026Q1")
    out, summary = handle_cases(df, cfg, set())
    assert set(out["primaryid"]) == {"P2", "P3"}
    assert summary["case_version"]["rows_excluded"] == 1