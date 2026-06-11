from __future__ import annotations

from dataclasses import dataclass
from re import Pattern
from typing import Literal

AttackSeverity = Literal["medium", "high", "critical"]


@dataclass(frozen=True, slots=True)
class AttackSignal:
    signal_id: str
    name: str
    pattern: Pattern[str]
    description: str


@dataclass(frozen=True, slots=True)
class AttackRule:
    rule_id: str
    name: str
    category: str
    severity: AttackSeverity
    description: str
    signals: tuple[AttackSignal, ...]
    min_signal_hits: int = 1

    def __post_init__(self) -> None:
        if not self.signals:
            raise ValueError("AttackRule requires at least one signal.")
        if self.min_signal_hits < 1:
            raise ValueError("AttackRule min_signal_hits must be >= 1.")
        if self.min_signal_hits > len(self.signals):
            raise ValueError("AttackRule min_signal_hits cannot exceed signal count.")


@dataclass(frozen=True, slots=True)
class AttackSignalMatch:
    rule_id: str
    signal_id: str
    line_no: int
    matched_text: str
    line_excerpt: str


@dataclass(frozen=True, slots=True)
class AttackRuleMatch:
    rule_id: str
    name: str
    category: str
    severity: AttackSeverity
    description: str
    matched_signals: tuple[str, ...]
    lines: tuple[int, ...]
    signal_matches: tuple[AttackSignalMatch, ...]


@dataclass(frozen=True, slots=True)
class AttackScanResult:
    blocked: bool
    highest_severity: AttackSeverity | None
    categories: tuple[str, ...]
    triggered_rules: tuple[AttackRuleMatch, ...]
    signal_matches: tuple[AttackSignalMatch, ...]

    def has_rule(self, rule_id: str) -> bool:
        return any(match.rule_id == rule_id for match in self.triggered_rules)
