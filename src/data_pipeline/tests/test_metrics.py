"""Tests for contingency table and deterministic statistics."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from data_pipeline.config import PipelineConfig
from data_pipeline.metrics import build_disproportionality
from data_pipeline.pair_generation import build_pair_universe


def _config(**overrides):
    defaults = dict(
        quarter="2026Q1",
        min_supporting_reports=3,
        min_prr=2.0,
        min_chi_square=4.0,
        haddane_anscombe_correction=0.0,
    )
    defaults.update(overrides)
    return PipelineConfig(**defaults)


def test_hand_calculated_pair_universe():
    """Reproduce the hand-crafted universe from conftest and verify exact values.

    Universe (observation level, N=5):
        ASPIRIN  x BLEEDING                  a=2
        ASPIRIN  x GASTROINTESTINAL BLEEDING a=2
        WARFARIN x HAEMORRHAGE               a=1

    n_drug: ASPIRIN=4, WARFARIN=1
    n_event: BLEEDING=2, GASTROINTESTINAL BLEEDING=2, HAEMORRHAGE=1
    N=5
    """

    cfg = _config()
    pairs = pd.DataFrame(
        {
            "primaryid": ["R001", "R001", "R002", "R003", "R003"],
            "caseid": ["C001", "C001", "C002", "C003", "C003"],
            "drug_name": ["ASPIRIN", "ASPIRIN", "WARFARIN", "ASPIRIN", "ASPIRIN"],
            "event_name": [
                "BLEEDING",
                "GASTROINTESTINAL BLEEDING",
                "HAEMORRHAGE",
                "BLEEDING",
                "GASTROINTESTINAL BLEEDING",
            ],
        }
    )
    m = build_disproportionality(pairs, cfg)

    aspirin_bleeding = m[(m["drug_name"] == "ASPIRIN") & (m["event_name"] == "BLEEDING")]
    row = aspirin_bleeding.iloc[0]
    assert int(row["a"]) == 2
    assert int(row["n_drug"]) == 4
    assert int(row["n_event"]) == 2
    N = 5
    b = 4 - 2  # n_drug - a
    c = 2 - 2  # n_event - a
    d = N - 4 - 2 + 2  # N - n_drug - n_event + a
    assert b == 2
    assert c == 0
    assert d == 1
    # PRR = (2/(2+2))/(0/(0+1)) -> undefined (0 denominator) -> should be None
    assert row["prr"] is None


def test_zero_counts_prr_none():
    """a=1, c=0 -> PRR denominator is 0/1 = 0 -> PRR should be None (undefined)."""

    pairs = pd.DataFrame(
        {
            "primaryid": ["R1", "R2"],
            "caseid": ["C1", "C2"],
            "drug_name": ["DRUG_A", "DRUG_B"],
            "event_name": ["EVENT_Y", "EVENT_Z"],
        }
    )
    cfg = _config()
    m = build_disproportionality(pairs, cfg)
    assert len(m) == 2
    # No row should have a finite PRR because each event appears only once
    # for a single drug (c=0 -> denominator zero).
    assert m["prr"].isna().all()


def test_simple_positive_universe():
    """Universally positive counts (all a,b,c,d>0) -> PRR/ROR/chi2 finite."""

    pairs = pd.DataFrame(
        {
            "primaryid": ["R%02d" % i for i in range(24)],
            "caseid": ["C%02d" % i for i in range(24)],
            "drug_name": ["ASPIRIN"] * 12 + ["IBUPROFEN"] * 12,
            "event_name": (["BLEEDING"] * 8 + ["HEADACHE"] * 4) + (["BLEEDING"] * 3 + ["HEADACHE"] * 9),
        }
    )
    cfg = _config(min_supporting_reports=1)
    m = build_disproportionality(pairs, cfg)
    # ASPIRIN x BLEEDING: a=8, n_drug=12, n_event=11, b=4, c=3, d=24-12-11+8=9
    asa_bleed = m[(m["drug_name"] == "ASPIRIN") & (m["event_name"] == "BLEEDING")]
    row = asa_bleed.iloc[0]
    assert int(row["a"]) == 8
    assert int(row["b"]) == 4
    assert int(row["c"]) == 3
    assert int(row["d"]) == 9
    expected_prr = (8 / 12) / (3 / 12)  # (a/(a+b)) / (c/(c+d)) = 0.6667/0.25 = 2.6667
    assert math.isfinite(row["prr"])
    assert math.isclose(row["prr"], expected_prr, rel_tol=1e-6)
    assert math.isfinite(row["ror"])
    expected_ror = (8 * 9) / (4 * 3)
    assert math.isclose(row["ror"], expected_ror, rel_tol=1e-6)
    assert math.isfinite(row["chi_square"])


def test_prr_with_haldane_anscombe():
    """With HA correction 0.5, PRR is finite even when raw c=0."""

    pairs = pd.DataFrame(
        {
            "primaryid": ["R1", "R2", "R3"],
            "caseid": ["C1", "C2", "C3"],
            "drug_name": ["DRUG_A", "DRUG_A", "DRUG_B"],
            "event_name": ["EVENT_Y", "EVENT_Y", "EVENT_Z"],
        }
    )
    cfg = _config(min_supporting_reports=1, haddane_anscombe_correction=0.5)
    m = build_disproportionality(pairs, cfg)
    asa = m[(m["drug_name"] == "DRUG_A") & (m["event_name"] == "EVENT_Y")]
    assert len(asa) == 1
    row = asa.iloc[0]
    # a=2, c=0 -> raw denominator = (0)/(0+?)=0 -> PRR undefined
    # with HA+0.5, denominator is finite, PRR should be >0 finite
    assert math.isfinite(row["prr"])