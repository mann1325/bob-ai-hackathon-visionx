# Member 1 — Reproducibility

## Guarantee

Running `python -m data_pipeline.run_pipeline` twice with identical inputs
and configuration produces **byte-identical** data artifacts.  The
determinism holds at every stage:

- fixed column order and column set per table (schema-validated headers);
- stable row ordering (merge sort on natural keys);
- no execution-time randomness anywhere in the pipeline;
- the only time-varying field is `pipeline_manifest.generated_at_utc`,
  which is explicit provenance metadata and excluded from the data files;
  the data CSVs/JSONs carry no timestamps.

## Verification performed

1. Unit/integration suite: 55 tests pass (`src/data_pipeline/tests/`),
   including a byte-identical double-run test on synthetic fixtures.
2. Full-release verification: the pipeline was run twice against the real
   2026 Q1 ASCII files to two different output directories, and every data
   artifact (`drug_event_pairs.csv`, `signal_metrics.csv`,
   `candidate_signals.csv`, `candidate_signals.json`,
   `normalized_reports.csv`, `normalized_reports.json`,
   `data_quality_report.json`) was byte-identical between the runs.

## How to rerun

```powershell
$env:FAERS_DATA_DIR   = "C:\Users\Admin\Desktop\IBM\ASCII"
$env:FAERS_OUTPUT_DIR = "C:\Users\Admin\Desktop\IBM\pipeline_output"
python -m pytest src/data_pipeline/tests/                 # tests
python -m data_pipeline.run_pipeline                      # data pipeline
```

Command-line equivalents for `--data-dir`, `--output-dir`, `--quarter`,
`--delete-file` are described in `DATA_PIPELINE.md`.

## Input fingerprinting

`pipeline_manifest.json` records SHA-256 of every input file
(DEMO/DRUG/REAC and, when supplied, the delete list).  Given (input
digests, code revision, config) you can prove a given artifact was produced
by a given input set, or detect silently changed inputs.

## Library environment (canonical)

- Python 3.12.4 (Windows 10/11, PowerShell)
- pandas ≥ 2.2, < 3
- numpy ≥ 1.26, < 3
- scipy ≥ 1.13, < 2 (only the scalar helper for chi-square equivalence
  checks; production statistics are closed-form vectorized)
- jsonschema ≥ 4.21 (authoritative draft-07 spot checks — see `export.py`)
- pytest ≥ 8

`src/data_pipeline/requirements.txt` pins these ranges.  The pipeline uses
only the standard library plus the above list; it makes no network calls.

## Numeric determinism

- PRR/ROR/chi-square are computed in float64 with closed-form expressions
  (see `STATISTICAL_METHODS.md`); no sampling, no iterative fitting.
- Plotting/rounding: CSV output writes full precision; JSON serializes with
  Python default `repr`, which is deterministic for the same float value.
- Cross-machine float reproducibility is expected to be bit-stable for
  these expression forms on IEEE-754 hardware (CPython default).

## Fail-safety

If input columns change, a schema/header mismatch raises `SchemaError`
instead of mis-aligning.  If an ambiguity is detected (e.g. a behavioral
decision not covered by this document), the pipeline stops with a report
rather than guessing — see `DATA_QUALITY.md` findings for how such cases
were handled in 26Q1.