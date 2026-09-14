"""Data-quality ledger.

Every exclusion, malformed row, or non-conversion is recorded explicitly so
that the pipeline never hides a lossy transform. The ledger serialises to the
data-quality report artifact.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LedgerEntry:
    stage: str
    reason: str
    count: int
    detail: str = ""


@dataclass
class QualityLedger:
    entries: list[LedgerEntry] = field(default_factory=list)

    def add(self, stage: str, reason: str, count: int, detail: str = "") -> None:
        self.entries.append(LedgerEntry(stage=stage, reason=reason, count=count, detail=detail))

    def merge(self, other: "QualityLedger") -> None:
        self.entries.extend(other.entries)

    def to_dict(self) -> dict:
        return {
            "entries": [entry.__dict__ for entry in self.entries],
            "total_exclusions": sum(e.count for e in self.entries),
        }