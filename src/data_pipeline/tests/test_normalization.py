"""Tests for deterministic normalization and primary-suspect selection."""

from __future__ import annotations

import pandas as pd
import pytest

from data_pipeline.normalization import normalize_drug_name, normalize_drug_names, normalize_reaction, normalize_reactions
from data_pipeline.pair_generation import build_pair_universe
from data_pipeline.config import PipelineConfig


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("  AsPirin  ", "ASPIRIN"),
        ("ASPIRIN", "ASPIRIN"),
        ("Albuterol.", "ALBUTEROL"),
        ("   " , None),
        ("", None),
        (None, None),
        ("Methotrexate  Sodium", "METHOTREXATE SODIUM"),
        ("metoprOLOL  ,", "METOPROLOL"),
    ],
)
def test_normalize_drug_name(raw, expected):
    assert normalize_drug_name(raw) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Bleeding", "BLEEDING"),
        ("  Gastrointestinal bleeding ", "GASTROINTESTINAL BLEEDING"),
        ("", None),
        (None, None),
    ],
)
def test_normalize_reaction(raw, expected):
    assert normalize_reaction(raw) == expected


def test_vectorized_matches_scalar_for_drug_names():
    import pandas as pd
    samples = ["  AsPirin  ", "Albuterol.", "", None, "Methotrexate  Sodium", "   "]
    vec = normalize_drug_names(pd.Series(samples)).tolist()
    scalar = [normalize_drug_name(x) for x in samples]
    for v, s in zip(vec, scalar):
        assert (v is None) == (s is None)
        if v is not None:
            assert v == s


def test_vectorized_matches_scalar_for_reactions():
    import pandas as pd
    samples = ["Bleeding", "  Gastrointestinal bleeding ", "", None, "  x "]
    vec = normalize_reactions(pd.Series(samples)).tolist()
    scalar = [normalize_reaction(x) for x in samples]
    for v, s in zip(vec, scalar):
        assert (v is None) == (s is None)
        if v is not None:
            assert v == s


def test_build_pair_universe_ps_only():
    drug = pd.DataFrame(
        {
            "primaryid": ["R1", "R1", "R1", "R2", "R2"],
            "caseid": ["C1", "C1", "C1", "C2", "C2"],
            "drug_seq": ["1", "2", "3", "1", "2"],
            "role_cod": ["PS", "SS", "C", "PS", "PS"],
            "drugname": ["Aspirin", "Clopidogrel", "Omeprazole", "Warfarin", "Warfarin"],
        }
    )
    reac = pd.DataFrame(
        {
            "primaryid": ["R1", "R1", "R2", "R2"],
            "caseid": ["C1", "C1", "C2", "C2"],
            "pt": ["Bleeding", "Bleeding", "Haemorrhage", "Headache"],
        }
    )
    cfg = PipelineConfig(quarter="2026Q1")
    pairs, stats = build_pair_universe(drug, reac, {"R1", "R2"}, cfg)

    # Only PS drugs reach the pair universe.
    assert set(pairs["drug_name"]) == {"ASPIRIN", "WARFARIN"} or set(pairs["drug_name"]) == {"ASPIRIN"}
    # Aspirin -> Bleeding (dedup); Warfarin -> Haemorrhage + Headache
    asa = pairs[pairs["drug_name"] == "ASPIRIN"]
    assert len(asa) == 1 and asa.iloc[0]["event_name"] == "BLEEDING"
    war = pairs[pairs["drug_name"] == "WARFARIN"]
    assert set(war["event_name"]) == {"HAEMORRHAGE", "HEADACHE"}
    assert stats.unique_pairs == 3
    assert stats.normalized_drug_names_missing == 0
    assert stats.normalized_reactions_missing == 0


def test_build_pair_universe_dedup_reaction_within_report():
    drug = pd.DataFrame(
        {
            "primaryid": ["R1", "R1"],
            "caseid": ["C1", "C1"],
            "drug_seq": ["1", "2"],
            "role_cod": ["PS", "PS"],
            "drugname": ["Aspirin", "Aspirin"],
        }
    )
    reac = pd.DataFrame(
        {
            "primaryid": ["R1", "R1", "R1"],
            "caseid": ["C1", "C1", "C1"],
            "pt": ["Bleeding", "Bleeding", "Bleeding"],
        }
    )
    cfg = PipelineConfig(quarter="2026Q1")
    pairs, stats = build_pair_universe(drug, reac, {"R1"}, cfg)
    # same (report, drug, event) deduped even if source had duplicate rows
    assert set(pairs["drug_name"]) == {"ASPIRIN"}
    assert set(pairs["event_name"]) == {"BLEEDING"}
    assert len(pairs) == 1
    assert stats.reactions_before_norm == 3
    assert stats.unique_reactions_after_norm == 1


def test_build_pair_universe_missing_reaction_orphan_counted():
    drug = pd.DataFrame(
        {
            "primaryid": ["R1", "R2"],
            "caseid": ["C1", "C2"],
            "drug_seq": ["1", "1"],
            "role_cod": ["PS", "PS"],
            "drugname": ["Aspirin", "Warfarin"],
        }
    )
    reac = pd.DataFrame(
        {
            "primaryid": ["R1"],
            "caseid": ["C1"],
            "pt": ["Bleeding"],
        }
    )
    cfg = PipelineConfig(quarter="2026Q1")
    _, stats = build_pair_universe(drug, reac, {"R1", "R2"}, cfg)
    assert stats.orphan_ps_drugs_primaryids == 1  # R2 has no reactions
    assert stats.orphan_reactions_primaryids == 0
    assert stats.matched_primaryids == 1