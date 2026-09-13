"""Pipeline configuration and runtime policy.

Everything here is explicit and configurable. No hard-coded absolute paths;
input/output directories are supplied through configuration or environment
variables. All statistical thresholds are gathered in one place so that no
threshold is silently embedded in business logic.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

DEMO_COLUMNS = (
    "primaryid",
    "caseid",
    "caseversion",
    "i_f_code",
    "event_dt",
    "mfr_dt",
    "init_fda_dt",
    "fda_dt",
    "rept_cod",
    "auth_num",
    "mfr_num",
    "mfr_sndr",
    "lit_ref",
    "age",
    "age_cod",
    "age_grp",
    "sex",
    "e_sub",
    "wt",
    "wt_cod",
    "rept_dt",
    "to_mfr",
    "occp_cod",
    "reporter_country",
    "occr_country",
)

DRUG_COLUMNS = (
    "primaryid",
    "caseid",
    "drug_seq",
    "role_cod",
    "drugname",
    "prod_ai",
    "val_vbm",
    "route",
    "dose_vbm",
    "cum_dose_chr",
    "cum_dose_unit",
    "dechal",
    "rechal",
    "lot_num",
    "exp_dt",
    "nda_num",
    "dose_amt",
    "dose_unit",
    "dose_form",
    "dose_freq",
)

REAC_COLUMNS = (
    "primaryid",
    "caseid",
    "pt",
    "drug_rec_act",
)

OUTC_COLUMNS = (
    "primaryid",
    "caseid",
    "outc_cod",
)

# age_cod -> divide the raw age by this factor to obtain age in years.
AGE_UNIT_YEARS_DIVISOR = {
    "YR": 1.0,
    "MON": 12.0,
    "WK": 52.0,
    "DY": 365.25,
    "HR": 8766.0,
    "DEC": 1.0,
}

_FAERS_DATA_DIR = os.environ.get("FAERS_DATA_DIR")
_FAERS_OUTPUT_DIR = os.environ.get("FAERS_OUTPUT_DIR", "pipeline_output")
_FAERS_QUARTER = os.environ.get("FAERS_QUARTER", "2026Q1")
_FAERS_DELETE_FILE = os.environ.get("FAERS_DELETE_FILE")


@dataclass(frozen=True)
class TableSpec:
    """Definition of a single FAERS ASCII table for a quarter."""

    kind: str
    filename: str
    columns: tuple[str, ...]
    delimiter: str = "$"
    encoding: str = "utf-8"

    @property
    def n_columns(self) -> int:
        return len(self.columns)


def build_table_specs(quarter: str) -> dict[str, TableSpec]:
    """Build the standard file names for a quarter like 2026Q1 -> 26Q1 suffix.

    FAERS ASCII filenames use a 2-digit year + quarter suffix, e.g. DEMO26Q1.txt.
    """

    year_two_digits = quarter[2:4]
    suffix = f"{year_two_digits}Q{quarter[-1]}"
    return {
        "DEMO": TableSpec("demo", f"DEMO{suffix}.txt", DEMO_COLUMNS),
        "DRUG": TableSpec("drug", f"DRUG{suffix}.txt", DRUG_COLUMNS),
        "REAC": TableSpec("reac", f"REAC{suffix}.txt", REAC_COLUMNS),
        "OUTC": TableSpec("outc", f"OUTC{suffix}.txt", OUTC_COLUMNS),
    }


@dataclass(frozen=True)
class PipelineConfig:
    """Deterministic pipeline policy.

    Fields are frozen and intentionally plain-data so that a run is fully
    described by (config, input files, code revision).
    """

    quarter: str = _FAERS_QUARTER
    data_dir: Path = field(
        default_factory=lambda: Path(_FAERS_DATA_DIR).expanduser()
        if _FAERS_DATA_DIR
        else Path(".")
    )
    output_dir: Path = field(
        default_factory=lambda: Path(_FAERS_OUTPUT_DIR).expanduser()
    )
    deleted_cases_file: Path | None = field(
        default_factory=lambda: Path(_FAERS_DELETE_FILE).expanduser()
        if _FAERS_DELETE_FILE
        else None
    )

    tables: dict[str, TableSpec] = field(
        default_factory=lambda: build_table_specs(_FAERS_QUARTER)
    )

    # --- case / version handling -------------------------------------------
    case_version_policy: str = "latest"

    # --- drug role universe ------------------------------------------------
    analysis_drug_roles: frozenset[str] = frozenset({"PS"})

    # --- deleted-case handling ---------------------------------------------
    # FDA distributes a per-quarter list of caseids that were removed after
    # publication. Application is opt-in and documented; the raw list is always
    # parsed and reported in the quality ledger.
    exclude_deleted_cases: bool = field(
        default_factory=lambda: os.environ.get("FAERS_EXCLUDE_DELETED_CASES", "").strip().lower()
        in ("1", "true", "yes", "on")
    )

    # --- statistical policy -------------------------------------------------
    min_supporting_reports: int = 3
    min_prr: float = 2.0
    min_chi_square: float = 4.0

    # 0.0 = raw formulas. A Haldane-Anscombe correction (0.5) is available to
    # stabilise zero cells and is applied ONLY when this value is non-zero.
    haddane_anscombe_correction: float = 0.0

    # Whether chi-square uses Yates' continuity correction (scipy default off).
    chi_square_continuity: bool = False

    ror_ci_include_lower: bool = True
    ror_ci_z: float = 1.96

    # Deterministic guard: only these source markers may appear in exports.
    source_marker: str = "FDA_FAERS"

    def __post_init__(self) -> None:
        # Accept plain strings and coerce to Path for consistent use everywhere.
        for name in ("data_dir", "output_dir", "deleted_cases_file"):
            value = getattr(self, name)
            if value is not None and not isinstance(value, Path):
                object.__setattr__(self, name, Path(value).expanduser())

    def resolve(self) -> "PipelineConfig":
        return self

    def schema_path(self, kind: str) -> Path:
        schemas = Path(__file__).resolve().parent / "schemas"
        mapping = {
            "normalized_report": schemas / "data-schema.json",
            "candidate_signal": schemas / "signal-schema.json",
        }
        return mapping[kind]

    def table_path(self, kind: str) -> Path:
        return self.data_dir / self.tables[kind].filename

    def require_files(self) -> list[Path]:
        missing = []
        for kind in ("DEMO", "DRUG", "REAC"):
            if not self.table_path(kind).is_file():
                missing.append(self.table_path(kind))
        return missing