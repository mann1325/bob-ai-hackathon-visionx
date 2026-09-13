# WORK_SCOPE.md — Member 1 (Data Engineer / Data Analyst)

Team: SignalTrace (VisionX). Branch: `feature/data-pipeline`.
Scope owner: Member 1. Document created in Phase 0. Schema contracts are the
team's shared JSON-Schemas in `SignalTrace_Team_Roles_and_Schemas/shared-schemas/`
(with the repo convention that exports must conform to them).

> NOTE: Fields such as `signal_id`, `drug_name`, `event_name`,
> `supporting_report_count`, `prr`, `candidate_status`, `ror`, `dataset_version`
> follow the shared `signal-schema.json`; normalized reports follow the shared
> `data-schema.json`. I do NOT generate `risk_score`, `priority_level`,
> `trend_score` — those belong to the AI/ML layer.

## 1. My ownership

FDA FAERS/AEMS data ingestion → validation → preprocessing → case/version
handling → primary-suspect logic → deterministic normalization → drug–event
pair generation → contingency tables → deterministic statistics (PRR, chi-square,
ROR) → candidate signal detection → data-quality reporting → validated export
for Member 2 (AI/risk), backend (Member 3), and frontend (Member 4/IBM Bob).

Pipeline + scope contract for **2026 Q1** (January 1 – March 31, 2026) release:
`DEMO26Q1.txt`, `DRUG26Q1.txt`, `REAC26Q1.txt` (plus `OUTC26Q1.txt` available
for outcome/severity features, and `DELETE26Q1.txt` for withdrawn-case handling,
if adopted by the team).

## 2. Files I may modify (my branch only)

Anything under these directories (created by me on `feature/data-pipeline`):

| Path | Purpose |
|---|---|
| `src/data_pipeline/` | All pipeline code + tests (module layout per team plan) |
| `src/data_pipeline/requirements.txt` | My dependency manifest (pandas, numpy, scipy, jsonschema) |
| `src/data_pipeline/pytest.ini` | Test discovery for my module |
| `docs/member1/` | My documentation (WORK_SCOPE, EXISTING_PIPELINE_AUDIT, DATA_PIPELINE, DATA_DICTIONARY, STATISTICAL_METHODS, DATA_QUALITY, REPRODUCIBILITY) |

Nothing else. No modifications to anything under `src/backend/`, `frontend/`,
`.github/`, root config, or shared docs, even if I observe bugs.

## 3. Files I must NOT modify

- `src/backend/**` (FastAPI routes/api/services/ai/rules/database/models, tests) — Member 3 / backend
- `src/shared/**` (missing today; if created by teammates, it is shared infra — report, don't edit)
- `frontend/**` (Next.js UI, adapters, mock data, components) — frontend team / IBM Bob
- `.github/**`, `CONTRIBUTING.md`, `README.md`, `submission.yaml` — shared/meta
- `docs/**` (except my own `docs/member1/`) — shared documentation
- Any teammate's branch or branch content

Rule: if a file is not in section 2, I do not touch it. Bugs in others' scope
are reported, not fixed.

## 4. Shared contracts I must honor (read-only usage)

- `data-schema.json` (Normalized Report): required `report_id`, `drug_name`,
  `reactions[]`, `report_quarter`; optional `patient_age`, `patient_sex`,
  `event_date`, `source` (const `FDA_FAERS`); `additionalProperties: false`.
- `signal-schema.json` (Candidate Signal): required `signal_id`, `drug_name`,
  `event_name`, `supporting_report_count`, `prr`, `candidate_status`;
  optional `ror`, `dataset_version`; `additionalProperties: false`.
- `document-analysis-schema.json`: consumed by Gemini layer; I do not emit this.
- Contract change requires team approval (CHANGE_POLICY LOCK rule). I will not
  change these files; my exports adapt to them.

### 5.1 Internal analytical data (free-form, not shared)
`report_id`, `caseid`, `primaryid`, `drug_name`, `event_name`, `report_quarter`,
`patient_age`, `patient_sex`, `event_date`, `source`, plus statistics columns
(`a`,`b`,`c`,`d`,`prr`,`ror`,`chi_square`,`ror_ci_lower`). These live in CSV
exports/`pipeline_output/` and are NOT constrained by the shared JSON schemas.
They are STAGE outputs, not API contracts.

## 5.2 Source of truth / allowed references

- Official FDA FAERS/AEMS 2026 Q1 ASCII (source of truth). No synthetic data in
  production; no substitution with Kaggle/other datasets.
- Machine-Geist FAERS signal-detection repository: reference/foundation for
  ideas and thresholds only. Adapted logic must be validated against this
  project's requirements and documented; never blind copies.

## 6. Expected outputs (pipeline_run to `pipeline_output/`, configurable)

| # | File | Format | Conforms to |
|---|---|---|---|
| 1 | `normalized_reports.csv` | CSV | data-schema.json (validated) |
| 2 | `drug_event_pairs.csv` | CSV | internal analytical |
| 3 | `signal_metrics.csv` | CSV | internal analytical |
| 4 | `candidate_signals.csv` + `.json` | CSV+JSON | signal-schema.json (validated) |
| 5 | `data_quality_report.json` | JSON | internal |
| 6 | `pipeline_manifest.json` | JSON | internal (determinism/metadata) |

## 7. Dependencies on other members

| On | What I need | What I hand off |
|---|---|---|
| Member 2 (AI/ML) | nothing to build my pipeline; will consume my candidate signals + metrics | candidate_signals.csv/json (incl. PRR/ROR/counts) |
| Backend (Member 3) | existing DB models/routes remain untouched by me; they consume my exports | normalized_reports + candidate_signals + metrics |
| Frontend (Member 4) | nothing | finalized candidate signal JSON (via backend) |
| Team (shared schemas) | stable `data-schema.json` / `signal-schema.json` | conformant exports |

## 8. Engineering principles (fixed)

Deterministic, reproducible, validated, auditable, traceable. No silent row
deletion, no undocumented filtering, no arbitrary thresholds, no hidden
transformations, no random behavior. All exclusions are counted and explained
(see DATA_QUALITY.md).

## 9. Medical/safety language (fixed)

Outputs/phrases must say "statistical signal", "candidate signal", "reported
association", "requires further investigation". Never "causes"/"unsafe"/
"FAERS proves causality".

## 10. Workflow discipline

Every phase ends with: tests → validation → row-count check → `git status` /
`git branch --show-current` → summary (completed/verified/failed/remaining).
If a phase's verification fails, STOP before proceeding.