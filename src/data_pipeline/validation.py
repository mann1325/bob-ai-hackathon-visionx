"""Schema and structural validation for FAERS ASCII tables.

Validation is strict: a column mismatch raises rather than silently proceeding.
Row-level problems are not fatal; they are counted and surfaced through
load statistics so that no record is ever silently dropped.
"""

from __future__ import annotations

import pandas as pd

from .config import TableSpec


class SchemaError(Exception):
    """Raised when a file header does not match the expected schema."""


class MissingFileError(Exception):
    """Raised when a required FAERS file is absent."""


class EmptyFileError(Exception):
    """Raised when a FAERS file contains no rows."""


def validate_columns(df: pd.DataFrame, spec: TableSpec) -> None:
    """Require an exact match between the file header and the expected columns.

    Order-sensitive so that later vectorized operations bind to explicit names
    deterministically. Extra or missing columns raise SchemaError with details.
    """

    actual = list(df.columns)
    expected = list(spec.columns)
    if actual == expected:
        return
    missing = [c for c in expected if c not in actual]
    extra = [c for c in actual if c not in expected]
    out_of_order = actual != expected
    raise SchemaError(
        "Column schema mismatch for table '%s': missing=%s extra=%s in_order=%s"
        % (spec.filename, missing, extra, not out_of_order)
    )


def validate_no_unexpected_nulls(df: pd.DataFrame, spec: TableSpec) -> None:
    """Sanity check that foreign-key identifiers are never empty.

    The loader translates empty cells to '' (keep_default_na=False). Rows with
    missing primaryid/caseid cannot be traced and must be surfaced, not dropped.
    """

    for col in ("primaryid", "caseid"):
        if col not in df.columns:
            continue
        n_empty = int((df[col].astype(str).str.strip() == "").sum())
        if n_empty:
            raise SchemaError(
                "Table '%s' contains %d rows with empty '%s' that break "
                "traceability; refusing to continue silently."
                % (spec.filename, n_empty, col)
            )