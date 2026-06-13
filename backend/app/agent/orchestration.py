from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Literal

from app.ai.schemas import ChatTurn


AgentName = Literal[
    "CoordinatorAgent",
    "WebSearchAgent",
    "CodeSandboxAgent",
    "LoopAgent",
    "GuardrailSafetyAgent",
    "ReportWriterAgent",
]


@dataclass(frozen=True, slots=True)
class AgentTraceStep:
    agent: AgentName
    action: str
    status: str
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class SafetyDecision:
    allowed: bool
    enabled: bool
    reason: str | None = None
    response: str | None = None


@dataclass(slots=True)
class OrchestrationTrace:
    steps: list[AgentTraceStep] = field(default_factory=list)

    def add(self, agent: AgentName, action: str, status: str, detail: str | None = None) -> None:
        self.steps.append(AgentTraceStep(agent=agent, action=action, status=status, detail=detail))

    def as_metadata(self) -> list[dict[str, str | None]]:
        return [
            {
                "agent": step.agent,
                "action": step.action,
                "status": step.status,
                "detail": step.detail,
            }
            for step in self.steps
        ]


class GuardrailSafetyAgent:
    _blocked_patterns = (
        re.compile(r"\b(ignore|bypass|disable)\b.*\b(policy|guardrail|safety|system)\b", re.I),
        re.compile(r"\b(api[_ -]?key|password|refresh token|access token|jwt|secret)\b", re.I),
        re.compile(r"\b(exfiltrate|steal|dump|leak)\b", re.I),
        re.compile(r"\bmetadata\.google\.internal\b|\b169\.254\.169\.254\b", re.I),
    )

    def __init__(self, *, enabled: bool) -> None:
        self.enabled = enabled

    async def check(self, *, prompt: str, messages: list[ChatTurn]) -> SafetyDecision:
        if not self.enabled:
            return SafetyDecision(allowed=True, enabled=False)
        text = "\n".join([*(message.content for message in messages[-6:]), prompt])
        for pattern in self._blocked_patterns:
            if pattern.search(text):
                return SafetyDecision(
                    allowed=False,
                    enabled=True,
                    reason="guardrail_policy_denied",
                    response=(
                        "Yêu cầu này bị chặn bởi Guardrail/Safety Agent vì có dấu hiệu yêu cầu "
                        "bỏ qua chính sách, truy cập bí mật, hoặc truy cập hạ tầng nội bộ."
                    ),
                )
        return SafetyDecision(allowed=True, enabled=True)


class WebSearchAgent:
    name: AgentName = "WebSearchAgent"


class CodeSandboxAgent:
    name: AgentName = "CodeSandboxAgent"


class LoopAgent:
    name: AgentName = "LoopAgent"

    def __init__(self, *, max_iterations: int) -> None:
        self.max_iterations = max_iterations


class ReportWriterAgent:
    name: AgentName = "ReportWriterAgent"

    def blocked_response_metadata(self, *, trace: OrchestrationTrace, decision: SafetyDecision) -> dict[str, Any]:
        return {
            "tool_name": "guardrail",
            "tool_status": "denied",
            "guardrail": {
                "enabled": decision.enabled,
                "allowed": decision.allowed,
                "reason": decision.reason,
            },
            "orchestration": trace.as_metadata(),
        }


class CoordinatorAgent:
    name: AgentName = "CoordinatorAgent"

    def __init__(self, *, guardrail_enabled: bool, max_loop_iterations: int) -> None:
        self.trace = OrchestrationTrace()
        self.guardrail = GuardrailSafetyAgent(enabled=guardrail_enabled)
        self.web_search = WebSearchAgent()
        self.code_sandbox = CodeSandboxAgent()
        self.loop = LoopAgent(max_iterations=max_loop_iterations)
        self.report_writer = ReportWriterAgent()
