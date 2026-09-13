"""SignalTrace Member 1 — deterministic FDA FAERS/AEMS data pipeline.

Ownership: ingestion, validation, preprocessing, case/version handling,
primary-suspect selection, deterministic normalization, drug-event pair
generation, contingency tables, PRR / chi-square / ROR statistics, candidate
signal detection, data-quality reporting, and validated export.

Everything in this package is deterministic and reproducible for a fixed
input + configuration + code revision.
"""

__version__ = "0.1.0"