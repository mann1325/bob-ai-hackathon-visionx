# Member 1 — Statistical Methods

This document describes exactly how every numeric output is computed so the
results are reproducible and unambiguous.  Nothing here claims causality:
these are disproportionality/signal-detection statistics over spontaneous
reports, which are hypothesis-generating only.

## Analysis unit: the observation

After normalization, the analytical universe is `drug_event_pairs`: one row
per unique (report, drug, event) observation.  A *report* is a `primaryid`
that survived case/version handling.

- PS drug set: `role_cod = PS` only (configurable).
- Drug-name normalization: trim, uppercase, collapse whitespace, strip
  leading/trailing non-alphanumerics (idempotent, see `normalization.py`).
- Reaction normalization: trim, uppercase, collapse whitespace.
- Duplicate rows (including multiple dose rows, see `DATA_QUALITY.md`)
  collapse before the cartesian join so a (report, drug) or (report, event)
  appearing several times in the raw file never inflates counts.

## 2x2 contingency counts (per drug-event pair)

Let `N` = total observations, and for a given drug X / event Y:
`a = |X ∩ Y|`, `b = |X \ Y|`, `c = |Y \ X|`, `d = N − a − b − c`.

All four cells are stored in `signal_metrics.csv` for every pair, so the
numbers can be independently re-checked.

## PRR (Proportional Reporting Ratio)

```
PRR = (a / (a+b)) / (c / (c+d))
```

95% CI via the log-normal approximation:

```
se(ln PRR) = sqrt( 1/a − 1/(a+b) + 1/c − 1/(c+d) )
CI = exp( ln PRR ∓ z · se ),  z = 1.96
```

`PRR` is **null** whenever the denominator is zero (`c/(c+d) = 0`) or either
exposure is zero; it is never `inf`/`nan` in output.

## ROR (Reporting Odds Ratio)

```
ROR = (a·d) / (b·c)
```

95% CI via the Woolf log approximation:

```
se(ln ROR) = sqrt( 1/a + 1/b + 1/c + 1/d )
CI = exp( ln ROR ∓ z · se )
```

`ROR` is **null** when `b·c = 0`.

## Pearson chi-square

Closed-form 2x2 formula (identical to
`scipy.stats.chi2_contingency(table, correction=False)` — verified by unit
test):

```
chi2 = N · (a·d − b·c)² / [(a+b)·(c+d)·(a+c)·(b+d)]
```

If `chi_square_continuity=true`, Yates' correction `(|ad−bc| − N/2)` is used
in the numerator.

## Zero-cell policy and the Haldane–Anscombe correction

Default configuration uses the raw formulas; **zero cells yield null
metrics, never infinity**.  A Haldane–Anscombe `+0.5` addition to all cells
is available (`haddane_anscombe_correction = 0.5`) and, when enabled, is
applied to every cell before PRR/ROR/chi-square and the CI standard errors
are computed.  The correction is intentionally opt-in so the default run is
the most conservative, least transformed representation of the data.

## Candidate signal thresholds (defaults)

| Criterion | Default |
|---|---|
| `supporting_report_count` (a) | ≥ 3 |
| `prr` | ≥ 2.0 |
| `chi_square` | ≥ 4.0 |

Every criterion must pass; all thresholds are configurable and recorded in
the manifest.  Only finite metrics are thresholded — a `null` PRR can never
clear the filter.

## Signal identifiers

`signal_id = "SIG-" + SHA-256(drug ‖ 0x1F ‖ event).hexdigest()[:10].upper()`

Deterministic and stable across runs/quarters for the same (drug, event),
so downstream layers can reference a pair reproducibly.

## Age conversion (export only)

`age_cod` divisor map: YR=1, MON=12, WK=52, DY=365.25, HR=8766, DEC=1.
Failed/absent conversions and unknown `age_cod` values → `patient_age` null.
`patient_sex` is emitted only for `F`/`M`; all other codes → null.

## Non-causality note

PRR/ROR/chi-square measure report disproportionality.  They do not establish
causation, and high signals can reflect reporting bias, co-prescription,
confounding, or data artifacts.  No causal language is used in any artifact.