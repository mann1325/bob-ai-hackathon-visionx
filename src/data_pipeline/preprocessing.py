"""Deterministic typed conversion of raw FAERS demo rows.

Missing values are '' on load and become None here. Every derived value keeps a
declared source in the raw cells. Unparseable cells become None and are
counted by the quality ledger; no implicit filler values are invented.
"""

from __future__ import annotations

import pandas as pd

from .config import AGE_UNIT_YEARS_DIVISOR, PipelineConfig

DEMO_ID_COLS = ("primaryid", "caseid", "caseversion")


def _to_numeric(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip()
    return pd.to_numeric(s.where(s != ""), errors="coerce")


def parse_event_date(series: pd.Series) -> pd.Series:
    """Parse FAERS YYYYMMDD event dates to ISO ``YYYY-MM-DD`` strings.

    Invalid or empty cells become None (nothing invented).
    """

    s = series.astype(str).str.strip().where(series.astype(str).str.strip() != "")
    dt = pd.to_datetime(s, format="%Y%m%d", errors="coerce")
    out = pd.Series([None] * len(series), index=series.index)
    valid = dt.notna()
    out.loc[valid] = dt.loc[valid].dt.strftime("%Y-%m-%d")
    return out


def parse_age_years(age: pd.Series, age_cod: pd.Series) -> pd.Series:
    """Convert FAERS age + age_cod to age in years (float) per FDA unit codes.

    Age_cod values: YR years, MON months, WK weeks, DY days, HR hours,
    DEC decades. Unknown/empty unit -> None (documented; no assumption).
    """

    age_num = _to_numeric(age)
    unit = age_cod.astype(str).str.strip().str.upper()
    divisor = unit.map(AGE_UNIT_YEARS_DIVISOR).astype(float)
    years = age_num.divide(divisor.where(divisor.notna() & (divisor != 0)))
    return years.round(2).where(years.notna())


def parse_sex(sex: pd.Series) -> pd.Series:
    """Keep F/M; everything else (U, unknown, '', other) becomes None."""

    s = sex.astype(str).str.strip().str.upper()
    return s.where(s.isin(["F", "M"]))


def process_demo(demo: pd.DataFrame, config: PipelineConfig) -> tuple[pd.DataFrame, dict]:
    """Build a case-level frame with typed patient fields.

    Returns (frame, counts dict) where counts keeps audit numbers such as the
    number of event dates and ages that could not be parsed.
    """

    frame = demo.loc[:, list(DEMO_ID_COLS)].copy()
    frame["report_id"] = demo["primaryid"].astype(str)
    frame["caseid"] = demo["caseid"].astype(str)

    parsed_event = parse_event_date(demo["event_dt"])
    parsed_age = parse_age_years(demo["age"], demo["age_cod"])
    parsed_sex = parse_sex(demo["sex"])

    frame["event_date"] = parsed_event
    frame["patient_age"] = parsed_age
    frame["patient_sex"] = parsed_sex
    frame["report_quarter"] = config.quarter
    frame["source"] = config.source_marker

    counts = {
        "demo_rows": len(demo),
        "event_date_missing_or_invalid": int(parsed_event.isna().sum()),
        "age_missing_or_invalid": int(parsed_age.isna().sum()),
        "sex_not_f_or_m": int(parsed_sex.isna().sum()),
    }
    return frame, counts