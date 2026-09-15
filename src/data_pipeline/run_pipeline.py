"""End-to-end deterministic FDA FAERS pipeline runner.

Usage::

    python -m data_pipeline.run_pipeline --data-dir <path> \
        --output-dir <path> [--quarter 2026Q1]

The runner writes the following artifacts to ``output_dir``:

- ``normalized_reports.csv``   normalized report rows (shared data-schema safe)
- ``drug_event_pairs.csv``     internal analytical pair universe
- ``signal_metrics.csv``       internal contingency + PRR/ROR/chi-square table
- ``candidate_signals.csv``    candidate signals (shared signal-schema safe)
- ``candidate_signals.json``   shared-contract JSON, schema validated
- ``normalized_reports.json``  shared-contract JSON, schema validated
- ``data_quality_report.json`` quality ledger
- ``pipeline_manifest.json``   provenance (input hashes, config, counts)

Timestamps appear only in the manifest; the data artifacts are deterministic.
"""

from __future__ import annotations

import argparse
import hashlib
import time
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .config import PipelineConfig
from .export import (
    build_candidate_signals,
    build_normalized_reports,
    write_datasets,
    write_json,
    write_pipeline_manifest,
    write_quality_report,
)
from .loaders import load_all
from .metrics import build_disproportionality
from .pair_generation import build_pair_universe
from .preprocessing import process_demo
from .case_processing import handle_cases
from .quality import QualityLedger
from .signal_detection import detect_signals, deterministic_signal_id


@dataclass
class PipelineResult:
    config: PipelineConfig
    manifest: dict
    reconciliation: dict

    def summary(self) -> str:
        lines = ["=" * 60, "SIGNALTRACE DATA PIPELINE — RECONCILIATION", "=" * 60]
        for stage, counts in self.reconciliation["stages"].items():
            lines.append("- %s: %s" % (stage, counts))
        lines.append("-" * 60)
        lines.append("candidate signals: %d" % self.reconciliation["signals"])
        lines.append("manifest: %s" % self.manifest["manifest_path"])
        return "\n".join(lines)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _stage(label: str, quiet: bool, start: float) -> float:
    if not quiet:
        print("[%6.1fs] %s" % (time.time() - start, label), flush=True)
    return time.time()


def run_pipeline(config: PipelineConfig, quiet: bool = False) -> PipelineResult:
    start = time.time()
    ledger = QualityLedger()
    # ---- 1. ingest ---------------------------------------------------------
    raw = load_all(config)
    _stage("ingest demo=%d drug=%d reac=%d outc=%d"
           % (len(raw.demo), len(raw.drug), len(raw.reac), len(raw.outc)), quiet, start)
    for kind, st in raw.load_stats.items():
        ledger.add("ingest/%s" % kind, "loaded", st.loaded_rows, st.to_dict())
        if st.rejected_rows:
            ledger.add("ingest/%s" % kind, "rejected", st.rejected_rows, st.to_dict())

    # ---- 2. demo -> typed cases -> case/version universe ------------------
    demo_typed, demo_counts = process_demo(raw.demo, config)
    for reason, count in demo_counts.items():
        ledger.add("preprocess/demo", reason, count)

    cases, case_summary = handle_cases(demo_typed, config, raw.deleted_case_ids)
    _stage("cases after version handling=%d" % len(cases), quiet, start)
    for reason, info in case_summary.items():
        if isinstance(info, dict):
            ledger.add("case_processing/%s" % reason, info.get("exclusion_reason", "ok"),
                       info.get("rows_excluded", 0), info)

    case_primaryids = set(cases["primaryid"].astype(str))

    # ---- 3. pairs -----------------------------------------------------------
    pairs, pair_stats = build_pair_universe(raw.drug, raw.reac, case_primaryids, config)
    _stage("pair generation unique_pairs=%d" % pair_stats.unique_pairs, quiet, start)
    ledger.add("pair_generation", "normalized_drug_names_missing",
               pair_stats.normalized_drug_names_missing)
    ledger.add("pair_generation", "normalized_reactions_missing",
               pair_stats.normalized_reactions_missing)
    ledger.add("pair_generation", "orphan_ps_drugs_primaryids",
               pair_stats.orphan_ps_drugs_primaryids)
    ledger.add("pair_generation", "orphan_reactions_primaryids",
               pair_stats.orphan_reactions_primaryids)

    # ---- 4. statistics ------------------------------------------------------
    metrics = build_disproportionality(pairs, config)
    metrics.insert(
        0,
        "signal_id",
        metrics.apply(
            lambda row: deterministic_signal_id(row["drug_name"], row["event_name"]),
            axis=1,
        ),
    )
    _stage("disproportionality metrics_rows=%d" % len(metrics), quiet, start)

    # ---- 5. candidates ------------------------------------------------------
    candidates, detect_stats = detect_signals(metrics, config)
    _stage("candidate signals=%d" % detect_stats.candidates_detected, quiet, start)
    for reason, count in detect_stats.__dict__.items():
        if reason.startswith("finite") and count == 0:
            ledger.add("signal_detection", reason, count)

    # ---- 6. normalized report export ----------------------------------------
    normalized_records = build_normalized_reports(pairs, cases, config)
    _stage("normalized report rows=%d" % len(normalized_records), quiet, start)

    # ---- 7. write artifacts --------------------------------------------------
    write_datasets(
        config,
        drug_event_pairs=pairs,
        signal_metrics=metrics,
        candidate_signals=candidates,
    )
    normalized_df = pd.DataFrame.from_records(normalized_records)
    write_datasets(config, normalized_reports=normalized_df)

    with open(config.schema_path("candidate_signal"), "r", encoding="utf-8") as fh:
        import json as _json
        signal_schema = _json.load(fh)
    candidate_records = build_candidate_signals(candidates, config, signal_schema)

    write_json(config, "candidate_signals", candidate_records)
    write_json(config, "normalized_reports", normalized_records)
    write_quality_report(config, ledger)
    _stage("data artifacts written", quiet, start)

    # ---- 8. manifest ---------------------------------------------------------
    input_files = {f.name: _sha256(f) for f in (config.table_path(k) for k in ("DEMO", "DRUG", "REAC"))}
    if config.deleted_cases_file and config.deleted_cases_file.is_file():
        input_files[config.deleted_cases_file.name] = _sha256(config.deleted_cases_file)

    manifest = {
        "quarter": config.quarter,
        "code_version": "0.1.0",
        "input_files_sha256": input_files,
        "config": {
            "case_version_policy": config.case_version_policy,
            "analysis_drug_roles": sorted(config.analysis_drug_roles),
            "exclude_deleted_cases": config.exclude_deleted_cases,
            "min_supporting_reports": config.min_supporting_reports,
            "min_prr": config.min_prr,
            "min_chi_square": config.min_chi_square,
            "haddane_anscombe_correction": config.haddane_anscombe_correction,
        },
        "load_stats": {k: st.to_dict() for k, st in raw.load_stats.items()},
        "counts": {
            "cases_after_version_handling": len(cases),
            "unique_pairs": pair_stats.unique_pairs,
            "metrics_rows": len(metrics),
            "candidate_signals": detect_stats.candidates_detected,
            "normalized_report_rows": len(normalized_records),
        },
        "excluded": {
            "case_version": case_summary.get("case_version", {}).get("rows_excluded", 0),
            "deleted_cases": case_summary.get("deleted_case_filter", {}).get("rows_excluded", 0),
        },
        "outcome": "completed",
    }
    manifest["manifest_path"] = "pipeline_manifest.json"
    manifest_path = write_pipeline_manifest(config, manifest)

    reconciliation = {
        "stages": {
            "raw_demo_rows": len(raw.demo),
            "raw_drug_rows": len(raw.drug),
            "raw_reac_rows": len(raw.reac),
            "cases_after_version_handling": len(cases),
            "ps_drug_names_after_dedup": pair_stats.unique_ps_drugs_after_norm,
            "unique_reactions": pair_stats.unique_reactions_after_norm,
            "matched_primaryids": pair_stats.matched_primaryids,
            "orphan_ps_drug_primaryids": pair_stats.orphan_ps_drugs_primaryids,
            "orphan_reaction_primaryids": pair_stats.orphan_reactions_primaryids,
            "unique_pairs": pair_stats.unique_pairs,
            "metrics_rows": len(metrics),
            "candidates": detect_stats.candidates_detected,
        },
        "signals": detect_stats.candidates_detected,
    }
    return PipelineResult(config=config, manifest=manifest, reconciliation=reconciliation)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="signal-trace-data-pipeline")
    parser.add_argument("--data-dir", help="FAERS ASCII directory (or FAERS_DATA_DIR)")
    parser.add_argument("--output-dir", help="Output directory (or FAERS_OUTPUT_DIR)")
    parser.add_argument("--quarter", help="Quarter label, e.g. 2026Q1 (or FAERS_QUARTER)")
    parser.add_argument("--delete-file", help="FAERS deleted-case list path (or FAERS_DELETE_FILE)")
    args = parser.parse_args(argv)

    import os
    config = PipelineConfig(
        quarter=args.quarter or os.environ.get("FAERS_QUARTER", "2026Q1"),
        data_dir=Path(args.data_dir or os.environ.get("FAERS_DATA_DIR") or "."),
        output_dir=Path(args.output_dir or os.environ.get("FAERS_OUTPUT_DIR", "pipeline_output")),
        deleted_cases_file=Path(args.delete_file) if args.delete_file else (
            Path(os.environ["FAERS_DELETE_FILE"]) if os.environ.get("FAERS_DELETE_FILE") else None
        ),
    )
    result = run_pipeline(config)
    print(result.summary())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())