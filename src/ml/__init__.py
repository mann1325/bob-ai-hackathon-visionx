"""SignalTrace ML Layer — Member 2.

Enriches candidate signals produced by the data pipeline with:
  - risk_score       : investigation-priority score (0.0–1.0)
  - priority_level   : enum low / medium / high / critical
  - trend_score      : reporting-trend indicator (null if single quarter)
  - rank             : deterministic ordinal rank per dataset version

Does NOT modify PRR, ROR, chi_square, or any other deterministic metric.
"""
