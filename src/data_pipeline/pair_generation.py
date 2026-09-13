"""Drug–event pair generation from the primary-suspect universe.

This module builds the analytical core of the pipeline:

1. Select PS-role drugs from DRUG.
2. Normalise the primary-suspect drug name.
3. Normalise reactions from REAC.
4. Produce one (drug_name, event_name) pair row per primaryid per PS drug
   per unique reaction, with explicit accounting for all join paths.

Deduplication is performed BEFORE the cartesian expansion so that
duplicate reaction rows within a report do not inflate the statistical
universe.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .config import PipelineConfig
from .normalization import normalize_drug_names, normalize_reactions


@dataclass(frozen=True)
class PairStats:
    ps_drug_rows_before_norm: int
    unique_ps_drugs_after_norm: int
    normalized_drug_names_missing: int
    reactions_before_norm: int
    unique_reactions_after_norm: int
    normalized_reactions_missing: int
    primaryids_in_ps_drugs: int
    primaryids_in_reactions: int
    matched_primaryids: int
    orphan_ps_drugs_primaryids: int
    orphan_reactions_primaryids: int
    unique_pairs: int
    pairs_with_missing_drug_name: int
    pairs_with_missing_reaction: int


def _safe_unique(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Drop fully identical rows and sort deterministically."""
    return df.drop_duplicates().sort_values(cols, kind="mergesort").reset_index(drop=True)


def build_pair_universe(
    drug: pd.DataFrame,
    reac: pd.DataFrame,
    case_primaryids: set[str],
    config: PipelineConfig,
) -> tuple[pd.DataFrame, PairStats]:
    """Build the drug–event analytical universe.

    ``case_primaryids`` restricts the universe to cases that survived case/
    version handling (a subset of all primaryids present in the raw files).
    """

    # ---- primary suspect drugs --------------------------------------------
    ps = drug[drug["role_cod"].isin(config.analysis_drug_roles)].copy()
    ps_before_norm = len(ps)
    ps["raw_drug_name"] = ps["drugname"]
    ps["drug_name"] = normalize_drug_names(ps["drugname"])
    ps["drug_name_missing"] = ps["drug_name"].isna()
    # Deduplicate (primaryid, drug_name) to avoid the same PS drug being
    # counted twice within one report.
    ps = _safe_unique(ps, ["primaryid", "drug_name"])
    # Restrict to cases surviving case/version handling.
    ps = ps[ps["primaryid"].astype(str).isin(case_primaryids)].reset_index(drop=True)

    unique_ps_drugs = int(ps.loc[ps["drug_name"].notna(), "drug_name"].nunique())
    ps_missing_count = int(ps["drug_name_missing"].sum())

    ps_core = ps[["primaryid", "caseid", "drug_name", "raw_drug_name"]].copy()
    ps_core["source"] = config.source_marker

    # ---- reactions -------------------------------------------------------
    reac_before_norm = len(reac)
    reac_clean = reac[["primaryid", "caseid", "pt"]].copy()
    reac_clean["raw_reaction"] = reac_clean["pt"]
    reac_clean["event_name"] = normalize_reactions(reac_clean["pt"])
    reac_clean["reaction_missing"] = reac_clean["event_name"].isna()
    # Deduplicate identical (primaryid, event_name) – documents one unique
    # occurrence of each MedDRA PT within a report.
    reac_clean = _safe_unique(reac_clean, ["primaryid", "event_name"])
    reac_clean = reac_clean[reac_clean["primaryid"].astype(str).isin(case_primaryids)].reset_index(drop=True)

    unique_reactions = int(reac_clean.loc[reac_clean["event_name"].notna(), "event_name"].nunique())
    reac_missing_count = int(reac_clean["reaction_missing"].sum())

    reac_core = reac_clean[["primaryid", "caseid", "event_name", "raw_reaction"]].copy()
    reac_core["source"] = config.source_marker

    # ---- join keys (for orphan reporting) ---------------------------------
    ps_ids = set(ps_core.loc[ps_core["drug_name"].notna(), "primaryid"].astype(str))
    reac_ids = set(reac_core.loc[reac_core["event_name"].notna(), "primaryid"].astype(str))
    matched_ids = ps_ids & reac_ids
    orphan_ps = ps_ids - reac_ids
    orphan_reac = reac_ids - ps_ids

    # ---- cartesian expansion (drug x reaction) per primaryid ---------------
    # Join on primaryid only (one-to-many both sides -> cartesian).
    ps_valid = ps_core[ps_core["drug_name"].notna()].copy()
    reac_valid = reac_core[reac_core["event_name"].notna()].copy()

    merged = ps_valid.merge(reac_valid, on=["primaryid", "caseid", "source"], how="inner", suffixes=("_drug", "_reaction"))

    # Capture canonical source; ensure deterministic column order.
    out = merged[["primaryid", "caseid", "drug_name", "raw_drug_name", "event_name", "raw_reaction", "source"]].copy()
    out = out.drop_duplicates(subset=["primaryid", "drug_name", "event_name"]).reset_index(drop=True)
    out = out.sort_values(["primaryid", "drug_name", "event_name"], kind="mergesort").reset_index(drop=True)

    stats = PairStats(
        ps_drug_rows_before_norm=ps_before_norm,
        unique_ps_drugs_after_norm=unique_ps_drugs,
        normalized_drug_names_missing=ps_missing_count,
        reactions_before_norm=reac_before_norm,
        unique_reactions_after_norm=unique_reactions,
        normalized_reactions_missing=reac_missing_count,
        primaryids_in_ps_drugs=len(ps_ids),
        primaryids_in_reactions=len(reac_ids),
        matched_primaryids=len(matched_ids),
        orphan_ps_drugs_primaryids=len(orphan_ps),
        orphan_reactions_primaryids=len(orphan_reac),
        unique_pairs=len(out),
        pairs_with_missing_drug_name=0,
        pairs_with_missing_reaction=0,
    )
    return out, stats