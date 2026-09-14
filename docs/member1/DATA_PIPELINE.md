# Member 1 — Data Pipeline (FDA FAERS 2026 Q1)

## Purpose

Deterministic, reproducible, audit-friendly ingestion and analysis of the
U.S. FDA Adverse Event Reporting System (FAERS) / AEMS quarterly ASCII
release.  The pipeline turns the raw `$`-delimited quarterly tables into a
normalized report set and a candidate-signal list for the upstream
SignalTrace decision layer.

Scope (this branch): `src/data_pipeline/**` and `docs/member1/**` only.

## Source of truth

- Official FAERS ASCII release, 2026 Q1 (files `DEMO26Q1.txt`,
  `DRUG26Q1.txt`, `REAC26Q1.txt`, `OUTC26Q1.txt`, local directory
  `C:\Users\Admin\Desktop\IBM\ASCII`).
- FDA quarterly *deleted case* list (optional, opt-in):
  `C:\Users\Admin\Desktop\IBM\Deleted\DELETE26Q1.txt` (6,135 case ids —
  see `DATA_QUALITY.md` for the verified zero intersection).
- The Machine-Geist repository was used as a **reference** for data shape
  only; all pipeline code is original.

## Architecture

```
ASCII files (DEMO/DRUG/REAC/OUTC 26Q1)
        │  csv.reader, $ delimiter, per-row field-count checks
        v
loaders (RawData + LoadStats)          <- nothing dropped unrecorded
        │
        v
preprocessing (process_demo)
        │  age→years (age_cod divisors), sex F/M only, event date ISO
        v
case/version handling (case_processing)
        │  latest-caseversion per caseid (tie-break primaryid desc)
        │  opt-in deleted-case filter (matches 0 in 26Q1 — documented)
        v
drug–event pair universe (pair_generation)
        │  PS role only; normalized drug name; normalized MedDRA PT
        │  dedupe (primaryid, drug_name) and (primaryid, event_name)
        │  cartesian join per report
        v
statistics (metrics)
        │  2x2 contingency at observation level (a,b,c,d,n_total)
        │  PRR + 95% CI (log-normal), ROR + 95% CI, Pearson chi-square
        v
signal detection (signal_detection)
        │  thresholds: a≥3, PRR≥2.0, chi2≥4.0 (configurable)
        │  deterministic signal_id = SHA-256(drug ▪ event) → SIG-…
        v
export (export.py)
        normalized_reports.csv/json   (shared data-schema, validated)
        candidate_signals.csv/json    (shared signal-schema, validated)
        drug_event_pairs.csv          (internal analytical universe)
        signal_metrics.csv            (contingency + statistics table)
        data_quality_report.json      (quality ledger)
        pipeline_manifest.json        (provenance + input hashes)
```

## Command

```powershell
$env:FAERS_DATA_DIR = "C:\Users\Admin\Desktop\IBM\ASCII"
$env:FAERS_OUTPUT_DIR = "C:\Users\Admin\Desktop\IBM\pipeline_output"
python -m data_pipeline.run_pipeline
```

Override any setting via CLI/flags instead:

```powershell
python -m data_pipeline.run_pipeline `
    --data-dir   "C:\Users\Admin\Desktop\IBM\ASCII" `
    --output-dir "C:\Users\Admin\Desktop\IBM\pipeline_output" `
    --quarter    2026Q1 `
    --delete-file "C:\Users\Admin\Desktop\IBM\Deleted\DELETE26Q1.txt"
```

## Configuration (env / PipelineConfig)

| Setting | Env var | Default | Meaning |
|---|---|---|---|
| data dir | `FAERS_DATA_DIR` | `.` | FAERS ASCII directory |
| output dir | `FAERS_OUTPUT_DIR` | `pipeline_output` | artifact directory |
| quarter | `FAERS_QUARTER` | `2026Q1` | release label |
| deleted list | `FAERS_DELETE_FILE` | unset | opt-in delete list path |
| exclude deleted | `FAERS_EXCLUDE_DELETED_CASES` | unset/false | apply the list |
| roles | `analysis_drug_roles` | `{PS}` | suspect-drug role universe |
| case policy | `case_version_policy` | `latest` | dedupe rule |
| min reports | `min_supporting_reports` | `3` | signal threshold |
| min PRR | `min_prr` | `2.0` | signal threshold |
| min chi2 | `min_chi_square` | `4.0` | signal threshold |
| HA correction | `haddane_anscombe_correction` | `0.0` | zero-cell stabilizer |
| chi2 continuity | `chi_square_continuity` | `false` | Yates correction |

No absolute paths are hard-coded; the repository contains no input data.

## Determinism

Two runs over identical inputs produce **byte-identical** data artifacts
(CSV/JSON content); the manifest additionally records input-file SHA-256
digests and a UTC timestamp.  Verified on the full 26Q1 release — see
`REPRODUCIBILITY.md`.

## Security / separation of concerns

- Only shared schemas are emitted, with `trend_score`, `risk_score`,
  `priority_level` always `null` (AI-layer fields).
- No credentials, no remote calls, no network access.
- All numeric outputs are finite-or-`null`; non-finite values are never
  written (see `STATISTICAL_METHODS.md`).
- Reports are observations, not causality claims (see
  `STATISTICAL_METHODS.md`).

## Bias to report, not assume

- Loader never silently drops rows: per-line field-count checks count every
  skipped line and expose it via `LoadStats` and the quality ledger.
- Deleted-case and orphan-report counts are always surfaced, even when zero.
- Ambiguities block rather than guess (see `DATA_QUALITY.md`).