"""Deterministic disproportionality statistics.

Implements PRR, chi-square, and ROR on the drug–event pair table produced by
``pair_generation``.  All calculations are performed at the pair-report level:
each row in the pair table represents one unique (primaryid, drug, event)
observation.  This is a standard disproportionality convention in
pharmacovigilance and is explicitly documented to avoid denominator confusion.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency

from .config import PipelineConfig


def prr_from_cells(a, b, c, d, correction: float = 0.0) -> float | None:
    """PRR from explicit cells: ``[a/(a+b)] / [c/(c+d)]``.

    Returns None (not infinity/NaN) whenever the numerator or denominator
    exposure is zero so that no non-finite number ever leaks into exports.
    """

    a, b, c, d = (float(x) + correction for x in (a, b, c, d))
    if a + b <= 0 or c + d <= 0:
        return None
    num = a / (a + b)
    denom = c / (c + d)
    if denom == 0.0:
        return None
    ratio = num / denom
    return ratio if math.isfinite(ratio) else None


def ror_from_cells(a, b, c, d, correction: float = 0.0) -> float | None:
    """ROR from explicit cells: ``ad / bc``. Returns None when bc == 0."""

    a, b, c, d = (float(x) + correction for x in (a, b, c, d))
    if b * c <= 0:
        return None
    ratio = (a * d) / (b * c)
    return ratio if math.isfinite(ratio) else None


def chi2_from_cells(a, b, c, d, continuity: bool = False, correction: float = 0.0) -> float | None:
    """Chi-square statistic from explicit 2x2 cells (scipy chi2_contingency)."""

    a, b, c, d = (float(x) + correction for x in (a, b, c, d))
    table = np.array([[a, b], [c, d]], dtype=float)
    if table.sum() <= 0:
        return None
    try:
        stat, _, _, _ = chi2_contingency(table.tolist(), correction=continuity)
        return float(stat)
    except Exception:
        return None


def build_disproportionality(pairs: pd.DataFrame, config: PipelineConfig) -> pd.DataFrame:
    """Compute deterministic 2x2 contingency tables and metrics for all pairs.

    Columns produced: drug_name, event_name, a, b, c, d, n_drug, n_event, n_total,
    prr, prr_ratio, prr_lower, prr_upper,
    chi_square, ror, ror_ci_lower, ror_ci_upper.
    """

    c = config.haddane_anscombe_correction

    # universe counts
    pair_count = len(pairs)
    drug_counts = (
        pairs.groupby("drug_name", sort=True)["primaryid"]
        .size()
        .rename("n_drug")
    )
    event_counts = (
        pairs.groupby("event_name", sort=True)["primaryid"]
        .size()
        .rename("n_event")
    )
    pair_counts = (
        pairs.groupby(["drug_name", "event_name"], sort=True)["primaryid"]
        .size()
        .rename("a")
        .reset_index()
    )

    # build contingency table rows
    df = pair_counts.copy()
    df = df.merge(drug_counts, on="drug_name", how="left")
    df = df.merge(event_counts, on="event_name", how="left")

    a = df["a"].astype(float)
    n_drug = df["n_drug"].astype(float)
    n_event = df["n_event"].astype(float)
    n_total = float(pair_count)

    b = n_drug - a
    c_col = n_event - a
    d = n_total - n_drug - n_event + a

    df["b"] = b.astype(int)
    df["c"] = c_col.astype(int)
    df["d"] = d.astype(int)
    df["n_drug"] = n_drug.astype(int)
    df["n_event"] = n_event.astype(int)
    df["n_total"] = int(n_total)

    a_c = a + c
    b_c = b + c
    c_col_c = c_col + c
    d_c = d + c

    # PRR
    with np.errstate(divide="ignore", invalid="ignore"):
        prr_num = a_c / (a_c + b_c)
        prr_denom = c_col_c / (c_col_c + d_c)
        prr_ratio = prr_num / prr_denom

    # PRR 95% CI (log-normal approximation)
    with np.errstate(divide="ignore", invalid="ignore"):
        se_prr = np.sqrt(
            1.0 / (a_c) - 1.0 / (a_c + b_c) + 1.0 / (c_col_c) - 1.0 / (c_col_c + d_c)
        )
        ln_prr = np.log(prr_ratio)
        z = config.ror_ci_z
        df["prr"] = prr_ratio
        df["prr_lower"] = np.exp(ln_prr - z * se_prr)
        df["prr_upper"] = np.exp(ln_prr + z * se_prr)

    # chi-square (Pearson, closed-form 2x2, vectorized).
    # Equivalent to scipy.stats.chi2_contingency(table, correction=False);
    # the scalar helper chi2_from_cells guards the scipy equivalence contract.
    a_int, b_int, c_int, d_int = (
        df["a"].to_numpy(dtype=float) + c,
        df["b"].to_numpy(dtype=float) + c,
        df["c"].to_numpy(dtype=float) + c,
        df["d"].to_numpy(dtype=float) + c,
    )
    n_corr = a_int + b_int + c_int + d_int
    diff = a_int * d_int - b_int * c_int
    if config.chi_square_continuity:
        # Yates' continuity correction: reduce |ad-bc| by N/2 before squaring.
        diff_c = np.abs(diff) - n_corr / 2.0
        diff = np.where(diff_c > 0.0, diff_c, 0.0)
    with np.errstate(divide="ignore", invalid="ignore"):
        denom = (a_int + b_int) * (c_int + d_int) * (a_int + c_int) * (b_int + d_int)
        numerator = n_corr * diff ** 2
        chi = np.where(denom > 0.0, numerator / denom, np.nan)
    df["chi_square"] = np.where(np.isfinite(chi), chi, None)

    # ROR
    with np.errstate(divide="ignore", invalid="ignore"):
        ror = (a_c * d_c) / (b_c * c_col_c)
        df["ror"] = ror
        # CI
        with np.errstate(divide="ignore", invalid="ignore"):
            se_ror = np.sqrt(1.0 / a_c + 1.0 / b_c + 1.0 / c_col_c + 1.0 / d_c)
            ln_ror = np.log(ror)
            df["ror_lower"] = np.exp(ln_ror - z * se_ror)
            df["ror_upper"] = np.exp(ln_ror + z * se_ror)

    # clean-up non-finite values: NaN/inf never leaks into exports (None used)
    for col in ("prr", "prr_lower", "prr_upper", "ror", "ror_lower", "ror_upper", "chi_square"):
        if col in df.columns:
            finite = np.isfinite(pd.to_numeric(df[col], errors="coerce").fillna(float("inf")).values)
            df[col] = df[col].astype(object).where(finite, None)

    # final deterministic sort
    df = df.sort_values(["drug_name", "event_name"], kind="mergesort").reset_index(drop=True)

    return df