from __future__ import annotations

from collections.abc import Sequence

from .rules import DEFAULT_ATTACK_RULES
from .schemas import AttackRule, AttackRuleMatch, AttackScanResult, AttackSeverity, AttackSignalMatch

_SEVERITY_ORDER: dict[AttackSeverity, int] = {
    "medium": 1,
    "high": 2,
    "critical": 3,
}


def scan_attack_simulation(
    content: str,
    *,
    rules: Sequence[AttackRule] = DEFAULT_ATTACK_RULES,
) -> AttackScanResult:
    lines = content.splitlines() or [content]
    triggered_rules: list[AttackRuleMatch] = []
    all_signal_matches: list[AttackSignalMatch] = []

    for rule in rules:
        signal_matches = _collect_signal_matches(rule, lines)
        matched_signal_ids = _ordered_unique(match.signal_id for match in signal_matches)
        if len(matched_signal_ids) < rule.min_signal_hits:
            continue

        rule_match = AttackRuleMatch(
            rule_id=rule.rule_id,
            name=rule.name,
            category=rule.category,
            severity=rule.severity,
            description=rule.description,
            matched_signals=tuple(matched_signal_ids),
            lines=tuple(_ordered_unique(match.line_no for match in signal_matches)),
            signal_matches=tuple(signal_matches),
        )
        triggered_rules.append(rule_match)
        all_signal_matches.extend(signal_matches)

    categories = tuple(_ordered_unique(match.category for match in triggered_rules))
    highest_severity = _highest_severity(triggered_rules)
    return AttackScanResult(
        blocked=bool(triggered_rules),
        highest_severity=highest_severity,
        categories=categories,
        triggered_rules=tuple(triggered_rules),
        signal_matches=tuple(all_signal_matches),
    )


def _collect_signal_matches(rule: AttackRule, lines: list[str]) -> list[AttackSignalMatch]:
    matches: list[AttackSignalMatch] = []
    seen: set[tuple[str, int, str]] = set()
    for signal in rule.signals:
        for line_no, line in enumerate(lines, start=1):
            for matched in signal.pattern.finditer(line):
                matched_text = matched.group(0).strip()
                if not matched_text:
                    continue
                key = (signal.signal_id, line_no, matched_text)
                if key in seen:
                    continue
                seen.add(key)
                matches.append(
                    AttackSignalMatch(
                        rule_id=rule.rule_id,
                        signal_id=signal.signal_id,
                        line_no=line_no,
                        matched_text=matched_text,
                        line_excerpt=_trim_excerpt(line),
                    )
                )
    return matches


def _highest_severity(triggered_rules: list[AttackRuleMatch]) -> AttackSeverity | None:
    if not triggered_rules:
        return None
    return max(triggered_rules, key=lambda match: _SEVERITY_ORDER[match.severity]).severity


def _ordered_unique(values):
    seen = set()
    ordered: list = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _trim_excerpt(line: str, *, max_chars: int = 160) -> str:
    collapsed = " ".join(line.strip().split())
    if len(collapsed) <= max_chars:
        return collapsed
    return f"{collapsed[: max_chars - 3]}..."


__all__ = ["scan_attack_simulation"]
