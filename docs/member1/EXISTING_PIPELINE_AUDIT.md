# EXISTING_PIPELINE_AUDIT.md — Phase 1

Audit date: 2026-09-13. Branch: `feature/data-pipeline`. Method: repository
tree inspection, targeted grep, and read-only probes of the 2026 Q1 FAERS files
with pandas (no repo files modified).

## 1. Existing data-pipeline components in the repo

| Component | Exists in repo? | Where | Verdict |
|---|---|---|---|
| FAERS ASCII ingestion / ETL | NO | — | **NEW** |
| FAERS loaders | NO | — | **NEW** |
| Case/version dedup logic | NO | — | **NEW** |
| Primary-suspect (PS) filtering | NO | — | **NEW** |
| Drug/reaction normalization | NO | — | **NEW** |
| Drug–event pair generation | NO | — | **NEW** |
| Contingency table | NO | — | **NEW** |
| PRR computation | NO (only PRR *column* consumed by backend/AI) | `src/backend/**` | **NEW** (mine) |
| ROR computation | NO | — | **NEW** |
| Chi-square computation | NO | — | **NEW** |
| Signal detection/thresholding | NO | — | **NEW** |
| Machine-Geist-derived code | NO | — | **NEW** (reference-only) |
| Normalized reports data model | PARTIAL (serving only) | `src/backend/database/models.py` (`ProcessedReportModel`: report_id, drug_name, reactions, report_quarter) | REUSE for naming cues only; column contract comes from shared schemas |
| FAERS quarterly metadata model | YES (consumes my exports) | `src/backend/database/models.py` (`FAERSQuarterlyMetadataModel`) | OUT OF SCOPE (backend) |
| Candidate signal serving | PARTIAL (reads `signals` table) | `src/backend/api/v1/signals.py` | OUT OF SCOPE (backend) |
| Regulatory rules engine | YES | `src/backend/rules/` | OUT OF SCOPE (backend) |
| Groq/Gemini AI | YES | `src/backend/ai/`, `src/backend/services/*` | OUT OF SCOPE |
| Frontend adapters/mocks | YES | `frontend/**` | OUT OF SCOPE |

## 2. Shared schema availability (contracts for my exports)

- In-repo: `src/shared/` does **NOT** exist (24 backend imports reference
  `shared.schemas.*`; backend currently does not import). This is shared
  infra — REPORTED, not fixed by me.
- Authoritative contracts live in the local workspace:
  `SignalTrace_Team_Roles_and_Schemas/shared-schemas/{data-schema.json,
  signal-schema.json, document-analysis-schema.json, api-contract.yaml}`.
- My exports must validate against `data-schema.json` and `signal-schema.json`.
  I will vendor **read-only copies** of these two schemas into
  `src/data_pipeline/schemas/` (consumed at export time) so validation is
  self-contained and reproducible.

## 3. Machine-Geist reference

Not present in the repo. Reference criteria to *validate* against project
requirements before adopting (defaults will live in `config.py` and be
documented): PRR ≥ 2, chi-square ≥ 4, supporting reports ≥ 3, plus documented
handling of zero/infinity/NaN.

## 4. FDA 2026 Q1 data reality (probed with pandas — FACT)

| File | rows | header cols (verified) | notes |
|---|---|---|---|
| `DEMO26Q1.txt` | 397,224 | primaryid,caseid,caseversion,i_f_code,event_dt,mfr_dt,init_fda_dt,fda_dt,rept_cod,auth_num,mfr_num,mfr_sndr,lit_ref,age,age_cod,age_grp,sex,e_sub,wt,wt_cod,rept_dt,to_mfr,occp_cod,reporter_country,occr_country | primaryid & caseid each fully unique (1:1); caseversion values 1–27 (91 distinct values); no empty caseversion; event_dt non-empty on 167,966; age present on 245,616 |
| `DRUG26Q1.txt` | 1,703,210 | primaryid,caseid,drug_seq,role_cod,drugname,prod_ai,val_vbm,route,dose_vbm,cum_dose_chr,cum_dose_unit,dechal,rechal,lot_num,exp_dt,nda_num,dose_amt,dose_unit,dose_form,dose_freq | roles: PS 463,454 / SS 566,003 / C 665,821 / I 7,692 / DN 240; no empty drugname; (primaryid,drug_seq) NOT unique → ~1.5M duplicate combos (investigate in pair phase) |
| `REAC26Q1.txt` | 1,330,675 | primaryid,caseid,pt,drug_rec_act | no empty pt; 12,389 unique normalized PTs; (primaryid,pt) NOT unique → investigate duplicates in pair phase |
| `OUTC26Q1.txt` | 291,581 | (from audit) primaryid-based outcomes | available for severity features |
| `Deleted/DELETE26Q1.txt` | 6,135 | removed case ids | adopt only if team agrees (deleted-case exclusion) |

Delimiter `$`, headers lowercase, missing cells are empty strings (no NA
literals observed). Expected counts from the brief (DEMO ≈ 397,224 / DRUG ≈
1,703,210 / REAC ≈ 1,330,675) MATCH exactly.

## 5. Classification summary

**NEW (implement on my branch):**
- `src/data_pipeline/` module: config, loaders, validation, preprocessing,
  normalization, case_processing, pair_generation, metrics, signal_detection,
  quality, export (+ `run_pipeline` entrypoint + tests + `requirements.txt`).
- `docs/member1/` documentation.

**REUSE (patterns only, not copied):**
- `ProcessedReportModel` field naming (`report_id/drug_name/reactions/report_quarter`) as a hint; shared schema is authoritative.
- Machine-Geist reference algorithms/approach (adapted + documented).

**ADAPT:** none (nothing exists to adapt).

**REPAIR:** none in my scope. (Discovered: missing `src/shared/schemas`,
missing `api/v1/ingest.py`, missing `src/.env.example` — all backend/shared,
reported in `08_risks_and_unknowns.md` of the repository audit; NOT my files.)

**OUT OF SCOPE:**
- `src/backend/**` (all), `frontend/**` (all), `.github/**`, root docs/config,
  shared schemas themselves, document-analysis schema.

## 6. Recommended implementation order

1. Module skeleton + `config.py` (policies, thresholds, paths) — later phases consume it.
2. `loaders.py` + `validation.py` (raw ingestion, schema/malformed checks).
3. `preprocessing.py` + `case_processing.py` (missing-value policy, case/version universe).
4. `normalization.py` (drug + reaction deterministic normalization).
5. `pair_generation.py` (PS universe → drug–event pairs; duplicate resolution).
6. `metrics.py` (contingency table, PRR, chi-square, ROR + CI).
7. `signal_detection.py` (thresholds → candidate signals; deterministic signal IDs).
8. `quality.py` (quality ledger at every stage) + `export.py` (schema-conformant outputs).
9. `run_pipeline.py` CLI; full-run reconciliation on 2026 Q1.
10. Tests throughout (unit + edge cases) and determinism double-run.
11. Documentation + git safety + commits + PR.

## 7. Verification (Phase 1 close-out)

- `git status` before change: clean (branch `feature/data-pipeline`).
- No unrelated files modified: only `docs/member1/WORK_SCOPE.md` added.
- Probe was read-only, executed from temp dir, no data written.