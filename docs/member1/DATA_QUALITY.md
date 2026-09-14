# Member 1 — Data Quality Report (FAERS 2026 Q1)

Verified counts for the full 2026 Q1 ASCII release, plus findings that
shaped the pipeline.  All counts are from a machine run over the official
files (`C:\Users\Admin\Desktop\IBM\ASCII`).

## Verified ingestion counts

| Table | Rows scanned | Rejected | Loaded |
|---|---|---|---|
| DEMO | 397,224 | 0 | 397,224 |
| DRUG | 1,703,210 | 0 | 1,703,210 |
| REAC | 1,330,675 | 0 | 1,330,675 |
| OUTC | 291,580 | 0 | 291,580 |

Zero malformed rows: every line matched its schema field count exactly, so
no row was dropped.  The loader is structured so that any future ragged line
is counted, not silently removed.

## Stage reconciliation (2026 Q1)

| Stage | Value |
|---|---|
| raw DEMO rows | 397,224 |
| cases after version handling | 397,224 (no duplicate `caseid` this quarter) |
| unique normalized PS drug names | 4,759 |
| unique normalized reaction terms | 12,389 |
| reports with ≥1 PS drug | 397,209 |
| reports with reactions but **no PS drug** | 15 |
| unique (drug, event) pairs | 1,311,393 |
| metric rows (unique drug–event pairs) | 373,012 |
| candidate signals (a≥3, PRR≥2, χ²≥4) | 48,894 |

**Clarification**: `metrics_rows` (373,012) is the number of unique
(drug, event) pairs with statistics, while `unique_pairs` (1,311,393)
counts report-level observation rows in `drug_event_pairs`.  Both are
exposed in the manifest and reconciliation summary.

## Findings affecting analysis

1. **Version handling is a no-op in 26Q1.** All `caseid` values are unique
   in this quarter's DEMO (caseversion 1..27 exist globally, but no case has
   two rows here).  The `latest` policy is still enforced for future
   quarters and is unit-tested.

2. **Duplicate structure in DRUG (26Q1).**
   - 1,703,210 rows, 1,501,182 unique (primaryid, drug_seq) keys.
   - 87,928 keys have multiple rows (289,956 rows).  Of these, only **~865
     are byte-identical duplicate rows**; the rest are multiple
     dose/route/administration records for the same `drug_seq` (e.g. XOLAIR
     150/225/375 mg rows).
   - The pipeline deduplicates to unique (report, normalized drug), so
     neither exact duplicates nor multi-dose rows inflate statistics.

3. **Duplicate structure in REAC (26Q1).**
   - 1,330,675 rows, 1,311,424 unique (primaryid, pt) keys.
   - 33,016 duplicate rows across 13,765 keys; ~19,183 are byte-identical
     (same `drug_rec_act` too).
   - Pipeline deduplicates to unique (report, normalized event).

4. **15 reaction-only reports.** 15 primaryids have reactions but their only
   drug role in the quarter is `DN` (deleted/other), e.g. device/product
   reports.  They are excluded from the pair universe and reported as
   `orphan_reaction_primaryids` in the ledger (never silent).

5. **Deleted-case list intersection is zero.** The supplied
   `DELETE26Q1.txt` (6,135 case ids) does not intersect any `caseid` or
   `primaryid` in the 26Q1 ASCII files (verified across DEMO/DRUG/REAC).
   The opt-in filter therefore excludes **0 rows**; this is surfaced as
   `deleted_ids_available=6135, matched=0` rather than assumed.  If the list
   is meant to apply to another release, point `FAERS_DELETE_FILE` at the
   matching file.

## Quality ledger

Every run writes `data_quality_report.json` with per-stage entries
(stage, reason, count, details).  Ingestion, preprocessing, case/version,
deleted-case, orphan and detection statistics are all present, so an
artifact can be audited back to the input files without re-running.

## Known limitations

- Normalization is formatting-only (no synonym mapping).  ``ASPIRIN`` and
  ``ASA`` remain distinct drug names in this release.
- `OUTC` is loaded and carried but not used in signal detection v0.1.0.
- `trend_score`, `risk_score`, `priority_level` are reserved for the AI
  layer and are always `null` in exports.
- The disease/reaction dictionary is FAERS's own PT terms; the pipeline does
  not recode PTs to a medical ontology.