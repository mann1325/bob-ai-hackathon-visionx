"""Deterministic text normalization for drug names and MedDRA Preferred Terms.

Rules are deliberately minimal (trim + uppercase + collapse repeated whitespace).
End-punctuation stripping keeps ``ASPIRIN``, ``ALBUTEROL.``, and
``METOPROLOL,`` from being treated as distinct values while preserving all
other characters identically. No semantic mapping, fuzzy matching, or active-
ingredient inference is performed.
"""

from __future__ import annotations

import re

import pandas as pd

# Leading / trailing ASCII punctuation that the pipeline strips.  The set is
# intentional and kept small to avoid conflating names that differ only by
# punctuation (e.g. hypothetical names ``DRUG-A`` vs ``DRUGA``).
_TRIMMER = re.compile(r"^[^A-Za-z0-9]+|[^A-Za-z0-9]+$")
_WHITESPACE = re.compile(r"\s+")


def normalize_drug_name(raw: str | None) -> str | None:
    """Normalise a DRUGNAME/PROD_AI to a canonical text form.

    Deterministic and idempotent. Returns None for blank / whitespace-only
    input so that exclusion in the pair-generation phase is explicit.
    """

    if not raw:
        return None
    s = str(raw).strip()
    if not s:
        return None
    s = s.upper()
    s = _WHITESPACE.sub(" ", s)
    s = _TRIMMER.sub("", s)
    return s if s else None


def normalize_reaction(raw_pt: str | None) -> str | None:
    """Normalise a MedDRA Preferred Term to the canonical form.

    The mapping is purely formatting (trim, uppercase, whitespace collapse)
    to match the normalisation style already present in the backend serving
    layer (``event_name`` stored uppercased).
    """

    if not raw_pt:
        return None
    s = str(raw_pt).strip()
    if not s:
        return None
    s = s.upper()
    s = _WHITESPACE.sub(" ", s)
    return s


def normalize_drug_names(raw: pd.Series) -> pd.Series:
    """Vectorized form of :func:`normalize_drug_name`.

    Mirrors the scalar semantics exactly (same regex operations) so bulk
    processing of the ingestion frames stays deterministic and byte-identical
    to a per-row call.
    """

    out = raw.astype("string").fillna("").str.strip().str.upper()
    out = out.str.replace(_WHITESPACE, " ", regex=True)
    out = out.str.replace(_TRIMMER, "", regex=True)
    return out.astype(object).mask(out.str.len() == 0, None)


def normalize_reactions(raw: pd.Series) -> pd.Series:
    """Vectorized form of :func:`normalize_reaction` (see note above)."""

    out = raw.astype("string").fillna("").str.strip().str.upper()
    out = out.str.replace(_WHITESPACE, " ", regex=True)
    return out.astype(object).mask(out.str.len() == 0, None)