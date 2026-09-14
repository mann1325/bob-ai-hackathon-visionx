"""Deterministic case/version handling.

FAERS/AEMS case IDs can appear across multiple quarterly releases with
increasing ``caseversion`` values.  This module selects the appropriate
representation according to the configured policy without silently deleting
any record.

The current default is ``latest``: for each caseid, keep only the primaryid
with the highest caseversion value, breaking ties by lexicographic primaryid
max to guarantee a single deterministic result.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .config import PipelineConfig


@dataclass(frozen=True)
class CaseVersionStats:
    total_input_rows: int
    unique_caseids_before: int
    unique_caseids_after: int
    rows_retained: int
    rows_excluded: int
    exclusion_reason: str
    case_version_policy: str


def select_latest_version(demo: pd.DataFrame) -> tuple[pd.DataFrame, CaseVersionStats]:
    """Keep the row with the highest ``caseversion`` per ``caseid``.

    Ties (very unlikely in FAERS) are broken deterministically by choosing the
    row with the lexicographically largest ``primaryid``.
    """

    if "caseversion" not in demo.columns:
        stats = CaseVersionStats(
            total_input_rows=len(demo),
            unique_caseids_before=demo["caseid"].nunique(),
            unique_caseids_after=len(demo),
            rows_retained=len(demo),
            rows_excluded=0,
            exclusion_reason="caseversion column missing; no dedup performed",
            case_version_policy="no_dedup",
        )
        return demo, stats

    caseid_unique_before = int(demo["caseid"].nunique())
    # Build sort key to get "best" primaryid per caseid: highest caseversion,
    # then highest primaryid lex (tie-break).
    df = demo.copy()
    df["_version_sort"] = df["caseversion"].astype(str).str.zfill(10)
    df["_primary_sort"] = df["primaryid"].astype(str).str.zfill(20)
    df = df.sort_values(["caseid", "_version_sort", "_primary_sort"], ascending=True, kind="mergesort")
    best = df.groupby("caseid", sort=False).tail(1).copy()
    best = best.drop(columns=["_version_sort", "_primary_sort"], errors="ignore")
    best = best.sort_values("primaryid", kind="mergesort").reset_index(drop=True)

    retained = len(best)
    excluded = len(demo) - retained
    stats = CaseVersionStats(
        total_input_rows=len(demo),
        unique_caseids_before=caseid_unique_before,
        unique_caseids_after=int(best["caseid"].nunique()),
        rows_retained=retained,
        rows_excluded=excluded,
        exclusion_reason="duplicate caseversion rows kept" if excluded else "all caseids unique",
        case_version_policy="latest",
    )
    return best, stats


def apply_deleted_case_filter(demo: pd.DataFrame, deleted_ids: set[str], config: PipelineConfig) -> tuple[pd.DataFrame, dict]:
    """Optionally exclude FDA-listed deleted cases.

    The filter is opt-in (config.exclude_deleted_cases). When disabled the
    count of available deleted IDs is still surfaced for audit purposes.
    """

    counts = {
        "deleted_ids_available": len(deleted_ids),
        "deleted_ids_matched_in_demo": 0,
        "rows_excluded": 0,
    }
    if not deleted_ids or not config.exclude_deleted_cases:
        return demo, counts

    mask = demo["caseid"].astype(str).isin(deleted_ids)
    matched = int(mask.sum())
    counts["deleted_ids_matched_in_demo"] = matched
    counts["rows_excluded"] = matched
    return demo.loc[~mask].reset_index(drop=True), counts


def handle_cases(demo: pd.DataFrame, config: PipelineConfig, deleted_ids: set[str]) -> tuple[pd.DataFrame, dict]:
    """Run full case/version handling pipeline on the DEMO frame.

    Returns a deduplicated frame and a summary dict for the quality ledger.
    """

    cases, cv_stats = select_latest_version(demo)
    filtered, del_stats = apply_deleted_case_filter(cases, deleted_ids, config)

    return filtered, {
        "case_version": {
            "total_input_rows": cv_stats.total_input_rows,
            "unique_caseids_before": cv_stats.unique_caseids_before,
            "unique_caseids_after": cv_stats.unique_caseids_after,
            "rows_retained": cv_stats.rows_retained,
            "rows_excluded": cv_stats.rows_excluded,
            "exclusion_reason": cv_stats.exclusion_reason,
            "case_version_policy": cv_stats.case_version_policy,
        },
        "deleted_case_filter": del_stats,
    }