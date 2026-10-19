"""Provenance tracking: every calculation records its data sources,
assumptions, out-of-range events and warnings so the UI can display them."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CalcRecord:
    label: str
    sources: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    out_of_range: list[str] = field(default_factory=list)
    parameters: dict = field(default_factory=dict)

    def source(self, s: str) -> "CalcRecord":
        if s not in self.sources:
            self.sources.append(s)
        return self

    def assume(self, s: str) -> "CalcRecord":
        if s not in self.assumptions:
            self.assumptions.append(s)
        return self

    def warn(self, s: str) -> "CalcRecord":
        if s not in self.warnings:
            self.warnings.append(s)
        return self

    def oor(self, s: str) -> "CalcRecord":
        if s not in self.out_of_range:
            self.out_of_range.append(s)
        return self


class Provenance:
    """Collector passed through engine calls; hands records to the UI."""

    def __init__(self):
        self.records: list[CalcRecord] = []

    def new(self, label: str, **params) -> CalcRecord:
        rec = CalcRecord(label=label, parameters=params)
        self.records.append(rec)
        return rec

    def merge(self, other: "Provenance"):
        self.records.extend(other.records)
