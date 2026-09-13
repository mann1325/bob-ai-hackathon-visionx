"""Ingestion of FDA FAERS ASCII files into typed DataFrame containers.

Loading rules:
- delimiter is ``$``
- every cell is read as text (empty cells stay '')
- column headers must match the expected schema exactly (see validation)
- rows whose field count differs from the schema are NOT silently discarded:
  they are dropped from the frame but counted in LoadStats.skipped_bad_lines so
  the quality ledger can reconcile scanned == accepted + rejected.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .config import PipelineConfig, TableSpec
from .validation import EmptyFileError, MissingFileError, SchemaError, validate_columns, validate_no_unexpected_nulls


@dataclass(frozen=True)
class LoadStats:
    """Per-table load accounting (absolute counts, nothing dropped unrecorded)."""

    filename: str
    scanned_data_lines: int
    loaded_rows: int
    skipped_bad_lines: int
    malformed_rows_kept: int

    @property
    def accepted_rows(self) -> int:
        return self.loaded_rows - self.malformed_rows_kept

    @property
    def rejected_rows(self) -> int:
        return self.skipped_bad_lines + self.malformed_rows_kept

    def to_dict(self) -> dict:
        return {
            "filename": self.filename,
            "scanned_data_lines": self.scanned_data_lines,
            "loaded_rows": self.loaded_rows,
            "skipped_bad_lines": self.skipped_bad_lines,
            "malformed_rows_kept": self.malformed_rows_kept,
            "accepted_rows": self.accepted_rows,
            "rejected_rows": self.rejected_rows,
        }


def _load_rows(path: Path, spec: TableSpec) -> tuple[list[list[str]], list[int]]:
    """Parse a FAERS ASCII file field-by-field.

    Returns (rows with exactly the expected field count, bad line numbers).
    Line numbers are 1-based physical lines (header included) so a bad row is
    greppable directly in the source file.
    """

    rows: list[list[str]] = []
    bad_line_numbers: list[int] = []
    with path.open("r", encoding=spec.encoding, newline="") as fh:
        reader = csv.reader(fh, delimiter=spec.delimiter)
        try:
            header = next(reader)
        except StopIteration:
            raise EmptyFileError("FAERS file is empty: %s" % path)
        if list(header) != list(spec.columns):
            raise SchemaError(
                "Column schema mismatch for table '%s': header=%r" % (spec.filename, header)
            )
        for line_no, fields in enumerate(reader, start=2):
            if len(fields) != spec.n_columns:
                bad_line_numbers.append(line_no)
                continue
            rows.append(fields)
    return rows, bad_line_numbers


def load_faers_table(path: Path, spec: TableSpec) -> tuple[pd.DataFrame, LoadStats]:
    """Load one FAERS ASCII table.

    Returns (DataFrame, LoadStats). Raises MissingFileError / EmptyFileError /
    SchemaError instead of silently continuing on structural problems.
    """

    if not path.is_file():
        raise MissingFileError("Missing required FAERS file: %s" % path)
    if path.stat().st_size == 0:
        raise EmptyFileError("FAERS file is empty: %s" % path)

    rows, bad_line_numbers = _load_rows(path, spec)

    scanned = len(rows) + len(bad_line_numbers)
    df = pd.DataFrame(rows, columns=list(spec.columns))
    validate_no_unexpected_nulls(df, spec)

    # Deterministic row order by natural keys.
    sort_cols = [c for c in ("primaryid", "caseid") if c in df.columns]
    df = df.sort_values(sort_cols, kind="mergesort").reset_index(drop=True)

    stats = LoadStats(
        filename=path.name,
        scanned_data_lines=scanned,
        loaded_rows=len(df),
        skipped_bad_lines=len(bad_line_numbers),
        malformed_rows_kept=0,
    )
    return df, stats


def load_deleted_cases(path: Path | None) -> set[str]:
    """Parse a FAERS quarterly deleted-case list (one caseid per line)."""

    if path is None or not path.is_file():
        return set()
    ids: set[str] = set()
    with path.open("r", encoding="utf-8") as fh:
        for raw in fh:
            cid = raw.strip()
            if cid:
                ids.add(cid)
    return ids


@dataclass(frozen=True)
class RawData:
    """Container for all loaded tables plus per-table load stats."""

    demo: pd.DataFrame
    drug: pd.DataFrame
    reac: pd.DataFrame
    outc: pd.DataFrame
    load_stats: dict[str, LoadStats]
    deleted_case_ids: set[str]

    @property
    def tables(self) -> dict[str, pd.DataFrame]:
        return {"DEMO": self.demo, "DRUG": self.drug, "REAC": self.reac, "OUTC": self.outc}


def load_all(config: PipelineConfig) -> RawData:
    """Load DEMO/DRUG/REAC/OUTC plus the deleted-case list for one quarter."""

    missing = config.require_files()
    if missing:
        raise MissingFileError("Missing required FAERS files: %s" % [str(p) for p in missing])

    loaded: dict[str, pd.DataFrame] = {}
    stats: dict[str, LoadStats] = {}
    for kind in ("DEMO", "DRUG", "REAC", "OUTC"):
        path = config.table_path(kind)
        if not path.is_file():
            continue
        df, st = load_faers_table(path, config.tables[kind])
        loaded[kind] = df
        stats[kind] = st

    deleted = load_deleted_cases(config.deleted_cases_file)

    return RawData(
        demo=loaded.get("DEMO", pd.DataFrame(columns=config.tables["DEMO"].columns)),
        drug=loaded.get("DRUG", pd.DataFrame(columns=config.tables["DRUG"].columns)),
        reac=loaded.get("REAC", pd.DataFrame(columns=config.tables["REAC"].columns)),
        outc=loaded.get("OUTC", pd.DataFrame(columns=config.tables["OUTC"].columns)),
        load_stats=stats,
        deleted_case_ids=deleted,
    )