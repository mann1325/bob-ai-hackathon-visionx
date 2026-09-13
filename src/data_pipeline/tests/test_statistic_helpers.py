"""Tests for explicit-cell statistics helpers (zero-count edge cases)."""

from __future__ import annotations

import math

import pytest

from data_pipeline.metrics import chi2_from_cells, prr_from_cells, ror_from_cells


def test_hand_calculated_example():
    # a=10, b=90, c=20, d=880
    # PRR = (10/100)/(20/900) = 0.1 / 0.02222... = 4.5
    prr = prr_from_cells(10, 90, 20, 880)
    assert math.isclose(prr, 4.5, rel_tol=1e-6)
    # ROR = (10*880)/(90*20) = 8800/1800 = 4.8888...
    ror = ror_from_cells(10, 90, 20, 880)
    assert math.isclose(ror, 4.888888888888889, rel_tol=1e-6)
    # chi-square positive finite
    chi2 = chi2_from_cells(10, 90, 20, 880)
    assert math.isfinite(chi2) and chi2 > 0


@pytest.mark.parametrize(
    "cells",
    [
        (0, 90, 20, 880),   # a=0
        (10, 0, 20, 880),   # b=0
        (10, 90, 0, 880),   # c=0
        (10, 90, 20, 0),    # d=0
        (0, 0, 0, 0),       # degenerate
    ],
)
def test_zero_cells_never_infinity(cells):
    prr = prr_from_cells(*cells)
    ror = ror_from_cells(*cells)
    chi2 = chi2_from_cells(*cells)
    # everything must be finite-or-None, never inf/nan
    for val in (prr, ror, chi2):
        assert val is None or math.isfinite(val)


def test_all_zero_returns_none():
    assert prr_from_cells(0, 0, 0, 0) is None
    assert ror_from_cells(0, 0, 0, 0) is None
    assert chi2_from_cells(0, 0, 0, 0) is None


def test_infinite_case_when_other_drugs_missing_event():
    # d=0 column (no "neither") is fine; but c=0 gives PRR denominator 0
    # c+d = 0+880 -> ok; c/(c+d)=0 -> ratio = inf? No: c=0 -> denom 0 -> prr None.
    assert prr_from_cells(10, 90, 0, 880) is None


def test_exact_equal_proportions():
    # identical exposure -> PRR = 1
    prr = prr_from_cells(5, 5, 25, 25)
    assert math.isclose(prr, 1.0, rel_tol=1e-9)


def test_closed_form_chi2_matches_scipy():
    import math
    from scipy.stats import chi2_contingency
    cases = [(10, 90, 20, 880), (1, 0, 0, 1), (50, 50, 50, 50), (2, 3, 4, 5)]
    for a, b, c, d in cases:
        expected, _, _, _ = chi2_contingency([[a, b], [c, d]], correction=False)
        a_f, b_f, c_f, d_f = (float(x) for x in (a, b, c, d))
        N = a_f + b_f + c_f + d_f
        denom = (a_f + b_f) * (c_f + d_f) * (a_f + c_f) * (b_f + d_f)
        chi_closed = N * (a_f * d_f - b_f * c_f) ** 2 / denom if denom > 0 else 0.0
        assert math.isclose(chi_closed, expected, rel_tol=1e-10)