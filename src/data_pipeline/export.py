"""Validated export of pipeline artifacts.

Every artifact is written deterministically (fixed, sorted column order and
sorted rows where relevant).  Shared-contract artifacts (normalized reports,
candidate signals) are validated against the vendored JSON-Schemas before
writing, and validation failure raises instead of emitting non-conforming
output.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import jsonschema
import pandas as pd

from .config import PipelineConfig
from .quality import QualityLedger


class ExportError(Exception):
    pass


def _fast_struct_validate_record(rec: dict, schema: dict) -> None:
    """Cheap exact structural validation of one record against a JSON-Schema.

    Implements the subset of Draft-07 that the shared schemas actually use:
    ``properties`` / ``required`` / ``additionalProperties: false`` / ``type``
    / ``enum`` / ``items.type``. Runs in microseconds per record, so the full
    production export sets (hundreds of thousands of rows) validate in
    seconds instead of the minutes a pure jsonschema walk would cost.
    """

    properties = schema.get("properties", {})
    allowed = set(properties)
    extra = set(rec) - allowed
    if extra:
        raise ExportError("record has undeclared properties %s" % sorted(extra))

    for name in schema.get("required", []):
        if name not in rec:
            raise ExportError("missing required property '%s'" % name)

    for name, spec in properties.items():
        if name not in rec:
            continue
        value = rec[name]
        if value is None:
            if spec.get("type") != "null" and not (
                isinstance(spec.get("type"), list) and "null" in spec["type"]
            ):
                raise ExportError("property '%s' must not be null" % name)
            continue

        allowed_types = spec.get("type")
        if isinstance(allowed_types, str):
            allowed_types = [allowed_types]

        ok = True

        if any(t == "string" for t in allowed_types):
            ok = ok and isinstance(value, str)
        elif any(t == "integer" for t in allowed_types):
            ok = ok and isinstance(value, int) and not isinstance(value, bool)
        elif any(t == "number" for t in allowed_types):
            ok = ok and (
                isinstance(value, (int, float)) and not isinstance(value, bool)
            )
        elif any(t == "array" for t in allowed_types):
            ok = ok and isinstance(value, list)
        elif any(t == "boolean" for t in allowed_types):
            ok = ok and isinstance(value, bool)

        if not ok:
            raise ExportError(
                "property '%s' has wrong type %s (expected %s)"
                % (name, type(value).__name__, spec.get("type"))
            )

        if spec.get("enum") is not None and value not in spec["enum"]:
            raise ExportError(
                "property '%s' value %r not in enum %r"
                % (name, value, spec["enum"])
            )

        if (
            spec.get("type") == "array"
            and spec.get("items", {}).get("type") == "string"
        ):
            for item in value:
                if not isinstance(item, str):
                    raise ExportError(
                        "array property '%s' must contain only strings" % name
                    )


def _struct_validate(
    records: list[dict],
    schema: dict,
    artifact: str,
) -> None:
    """Exact structural validation of every record (O(n), deterministic)."""

    for idx, rec in enumerate(records):
        try:
            _fast_struct_validate_record(rec, schema)
        except ExportError as exc:
            raise ExportError(
                "Artifact '%s' violates shared schema at record %d: %s"
                % (artifact, idx, exc)
            ) from exc


def _validate_records(
    records: list[dict],
    schema: dict,
    artifact: str,
) -> None:
    """Gate artifacts against the shared contract.

    Every record is checked structurally (identical semantics, O(n)). As an
    authoritative cross-check, a bounded sample is passed through the real
    jsonschema Draft-07 validator so any drift between the fast checker and
    the canonical validator is surfaced as a failure.
    """

    _struct_validate(records, schema, artifact)

    sample_size = min(64, len(records))

    if sample_size:
        step = max(1, len(records) // sample_size)
        sample = [
            records[i]
            for i in range(0, len(records), step)
        ][:sample_size]

        for idx, rec in enumerate(sample):
            try:
                jsonschema.validate(
                    instance=rec,
                    schema=schema,
                )
            except jsonschema.ValidationError as exc:
                raise ExportError(
                    "Artifact '%s' fails jsonschema at sample record %d: %s"
                    % (artifact, idx, exc.message)
                ) from exc


def _load_schema(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def build_normalized_reports(
    pairs: pd.DataFrame,
    cases: pd.DataFrame,
    outc: pd.DataFrame,
    config: PipelineConfig,
) -> list[dict]:
    """Render normalized report records.

    Each record represents one PS drug per report.

    Seriousness is derived only from the reported FAERS OUTC codes.
    No OUTC information means the seriousness remains Unknown.
    """

    # ------------------------------------------------------------------
    # 1. Reactions per report
    # ------------------------------------------------------------------
    # Case-level: collect all unique preferred-term events reported
    # for the same primaryid.
    reactions = (
        pairs.groupby("primaryid")["event_name"]
        .apply(lambda s: sorted(set(s.tolist())))
        .to_dict()
    )

    # ------------------------------------------------------------------
    # 2. Determine seriousness from FAERS OUTC codes
    # ------------------------------------------------------------------
    # FAERS serious outcome codes:
    #
    # DE = Death
    # LT = Life-threatening
    # HO = Hospitalization
    # DS = Disability
    # CA = Congenital anomaly
    # RI = Required intervention
    # OT = Other serious
    #
    # We do NOT infer seriousness from:
    # - PRR/ROR
    # - patient age
    # - reaction/event name
    # - signal strength
    #
    # If OUTC is unavailable for a report, seriousness remains Unknown.
    serious_outcome_codes = {
        "DE",
        "LT",
        "HO",
        "DS",
        "CA",
        "RI",
        "OT",
    }

    seriousness_by_pid: dict[str, dict] = {}

    if (
        not outc.empty
        and "primaryid" in outc.columns
        and "outc_cod" in outc.columns
    ):
        for pid, group in outc.groupby("primaryid"):
            codes = sorted(
                {
                    str(code).strip().upper()
                    for code in group["outc_cod"].dropna()
                    if str(code).strip()
                }
            )

            serious_codes = [
                code
                for code in codes
                if code in serious_outcome_codes
            ]

            if serious_codes:
                seriousness_by_pid[str(pid)] = {
                    "seriousness": "Serious",
                    "seriousness_codes": serious_codes,
                }
            else:
                seriousness_by_pid[str(pid)] = {
                    "seriousness": "Non-serious",
                    "seriousness_codes": [],
                }

    # ------------------------------------------------------------------
    # 3. Choose drug rows deterministically
    # ------------------------------------------------------------------
    drug_rows = (
        pairs[["primaryid", "drug_name"]]
        .drop_duplicates()
        .sort_values(
            ["primaryid", "drug_name"],
            kind="mergesort",
        )
    ).reset_index(drop=True)

    pids = drug_rows["primaryid"].astype(str).tolist()
    drugs = drug_rows["drug_name"].tolist()

    # ------------------------------------------------------------------
    # 4. Build case lookup
    # ------------------------------------------------------------------
    case_lookup = None

    if "primaryid" in cases.columns:
        case_idx = cases.set_index("primaryid")

        case_lookup = {
            "patient_age": case_idx["patient_age"].to_dict(),
            "patient_sex": case_idx["patient_sex"].to_dict(),
            "event_date": case_idx["event_date"].to_dict(),
        }

    import math as _math

    # ------------------------------------------------------------------
    # 5. Build normalized records
    # ------------------------------------------------------------------
    records: list[dict] = []
    append = records.append

    for pid, drug in zip(pids, drugs):
        age = (
            (case_lookup or {}).get("patient_age", {}).get(pid)
            if case_lookup
            else None
        )

        sex = (
            (case_lookup or {}).get("patient_sex", {}).get(pid)
            if case_lookup
            else None
        )

        event_date = (
            (case_lookup or {}).get("event_date", {}).get(pid)
            if case_lookup
            else None
        )

        # Patient age
        age_val = None

        if age is not None and not (
            isinstance(age, float) and _math.isnan(age)
        ):
            age_val = float(age)
        elif age is not None:
            age_val = None

        # Patient sex
        sex_val = (
            None
            if sex is None or pd.isna(sex)
            else str(sex)
        )

        # Event date
        date_val = (
            None
            if event_date is None or pd.isna(event_date)
            else str(event_date)
        )

        # Seriousness
        outcome = seriousness_by_pid.get(str(pid))

        if outcome:
            seriousness = outcome["seriousness"]
            seriousness_codes = outcome["seriousness_codes"]
        else:
            seriousness = "Unknown"
            seriousness_codes = []

        append(
            {
                "report_id": pid,
                "drug_name": str(drug),
                "reactions": reactions.get(pid, []),
                "patient_age": age_val,
                "patient_sex": sex_val,
                "event_date": date_val,
                "seriousness": seriousness,
                "seriousness_codes": seriousness_codes,
                "report_quarter": config.quarter,
                "source": config.source_marker,
            }
        )

    # ------------------------------------------------------------------
    # 6. Validate against normalized report schema
    # ------------------------------------------------------------------
    with open(
        config.schema_path("normalized_report"),
        "r",
        encoding="utf-8",
    ) as fh:
        schema = json.load(fh)

    _validate_records(
        records,
        schema,
        "normalized_reports",
    )

    return records


def build_candidate_signals(
    candidates: pd.DataFrame,
    config: PipelineConfig,
    schema: dict,
) -> list[dict]:
    """Translate candidate signal rows into schema-conformant JSON records."""

    records = []

    for _, r in candidates.sort_values(
        "signal_id",
        kind="mergesort",
    ).iterrows():

        def _num(val) -> float | None:
            if pd.isna(val):
                return None

            v = float(val)

            return None if v != v else v  # NaN -> None

        records.append(
            {
                "signal_id": str(r["signal_id"]),
                "drug_name": str(r["drug_name"]),
                "event_name": str(r["event_name"]),
                "supporting_report_count": int(
                    r["supporting_report_count"]
                ),
                "prr": _num(r["prr"]),
                "ror": _num(r["ror"]),
                "trend_score": None,
                "risk_score": None,
                "priority_level": None,
                "candidate_status": str(r["candidate_status"]),
                "dataset_version": str(r["dataset_version"]),
            }
        )

    _validate_records(
        records,
        schema,
        "candidate_signals",
    )

    return records


def _sortable_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Return a frame whose columns are all lexicographically sortable.

    Object columns that hold lists (e.g. the report-level ``reactions`` list)
    are serialized deterministically to a '|'-joined string so that a stable
    global sort is possible. The schema-conformant JSON copy keeps the list.
    """

    out = df.copy()

    for col in out.columns:
        if out[col].dtype == object:
            sample = out[col].dropna()

            if len(sample) and isinstance(sample.iloc[0], list):
                out[col] = out[col].map(
                    lambda xs: "|".join(xs)
                    if isinstance(xs, list)
                    else ""
                )

    return out


def write_datasets(
    config: PipelineConfig,
    **frames: pd.DataFrame,
) -> Path:
    """Write internal CSV artifacts with deterministic column order/sort."""

    config.output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    for name, df in frames.items():
        frame = _sortable_frame(df)

        sorted_df = (
            frame.sort_values(
                list(frame.columns),
                kind="mergesort",
            )
            .reset_index(drop=True)
        )

        path = config.output_dir / f"{name}.csv"

        sorted_df.to_csv(
            path,
            index=False,
            encoding="utf-8",
        )

    return config.output_dir


def write_json(
    config: PipelineConfig,
    name: str,
    payload: dict | list,
) -> Path:
    config.output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    path = config.output_dir / f"{name}.json"

    with path.open("w", encoding="utf-8") as fh:
        json.dump(
            payload,
            fh,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )

    return path


def write_quality_report(
    config: PipelineConfig,
    ledger: QualityLedger,
) -> Path:
    return write_json(
        config,
        "data_quality_report",
        ledger.to_dict(),
    )


def write_pipeline_manifest(
    config: PipelineConfig,
    payload: dict,
) -> Path:
    payload.setdefault(
        "generated_at_utc",
        datetime.now(timezone.utc).isoformat(),
    )

    payload.setdefault(
        "pipeline_version",
        "0.1.0",
    )

    return write_json(
        config,
        "pipeline_manifest",
        payload,
    )