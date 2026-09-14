# Member 1 — Data Dictionary

All pipelines produce the artifacts described below.  `drug_event_pairs.csv`,
`signal_metrics.csv`, `candidate_signals.csv` are analytical/build artifacts;
`normalized_reports.csv` / `normalized_reports.json` and
`candidate_signals.json` are the shared-contract outputs for the rest of the
SignalTrace system (schema-validated).

## normalized_reports (.csv / .json)

One row **per (report, PS drug)**.  ``reactions`` is the sorted list of all
unique normalized reaction terms observed for that report.

| Field | Type | Notes |
|---|---|---|
| `report_id` | string | FAERS `primaryid` of the retained case version |
| `drug_name` | string | normalized PS drug name (uppercase, trimmed) |
| `reactions` | list[string] | unique MedDRA PTs normalized (uppercase), sorted |
| `patient_age` | float|null | age in years (see `STATISTICAL_METHODS.md` §age) |
| `patient_sex` | string|null | `F` or `M` only; anything else → null |
| `event_date` | string|null | ISO-8601 `YYYY-MM-DD` from `event_dt` |
| `report_quarter` | string | e.g. `2026Q1` |
| `source` | string | constant `FDA_FAERS` |

## candidate_signals (.csv / .json)

One row per (drug, event) pair passing all thresholds.  Schema-conformant
`candidate_status="candidate"`.

| Field | Type | Notes |
|---|---|---|
| `signal_id` | string | `SIG-` + first 10 hex chars of SHA-256(`drug` ▪ `event`) |
| `drug_name` | string | normalized suspect drug |
| `event_name` | string | normalized reaction |
| `supporting_report_count` | integer | `a` (observation count for this pair) |
| `prr` | number|null | Proportional Reporting Ratio |
| `ror` | number|null | Reporting Odds Ratio |
| `trend_score` | null | reserved (AI layer) — always null |
| `risk_score` | null | reserved (AI layer) — always null |
| `priority_level` | null | reserved (AI layer) — always null |
| `candidate_status` | string | `candidate` |
| `dataset_version` | string | `2026Q1` |

## drug_event_pairs.csv (internal)

| Column | Notes |
|---|---|
| `primaryid` | surviving report id (source text) |
| `caseid` | case id |
| `drug_name` | normalized PS drug |
| `raw_drug_name` | verbatim `drugname` |
| `event_name` | normalized PT |
| `raw_reaction` | verbatim `pt` |
| `source` | `FDA_FAERS` |

## signal_metrics.csv (internal)

Per unique (drug, event): contingency cells and statistics.

| Column | Notes |
|---|---|
| `drug_name`, `event_name` | pair key |
| `a` | reports with drug AND event |
| `b` | reports with drug, without event |
| `c` | reports without drug, with event |
| `d` | reports without both |
| `n_drug` | observations with drug |
| `n_event` | observations with event |
| `n_total` | total observations (pair count) |
| `prr`, `prr_lower`, `prr_upper` | PRR + 95% log-normal CI |
| `ror`, `ror_lower`, `ror_upper` | ROR + 95% CI |
| `chi_square` | Pearson chi-square (closed-form, Yates optional) |

All counts are at the **observation level**: one row in `drug_event_pairs`
= one unique (report, drug, event).

## data_quality_report.json

Quality ledger entries: `{stage/kind, reason, count, details}` covering
ingest counts/rejects, preprocess overflow, case/version exclusions,
deleted-case availability/match, orphan reports, and signal-detection
stats.

## pipeline_manifest.json

Provenance: quarter, code/pipeline version, input-file SHA-256 digests,
effective config, `load_stats`, key output counts, exclusions, UTC
timestamp, outcome.

## FAERS contracts used by this pipeline

| Column | Source | Use |
|---|---|---|
| `primaryid` | DEMO/DRUG/REAC | report/analysis key |
| `caseid` | DEMO/DRUG/REAC | case grouping (multiple versions) |
| `caseversion` | DEMO | version selection (`latest`) |
| `event_dt`, `age`, `age_cod`, `sex` | DEMO | patient attributes (export only) |
| `drug_seq`, `role_cod`, `drugname` | DRUG | PS-role filter + normalization |
| `pt` | REAC | event normalization + pair axis |
| `outc_cod` | OUTC | carried but unused in v0.1.0 |