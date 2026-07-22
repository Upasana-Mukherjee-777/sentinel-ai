"""
services/agents/base.py

Every Sentinel AI agent, regardless of domain (call audio, WhatsApp text,
currency images, URLs, transactions...) returns the SAME explanation
contract. This is the "Explainable AI Framework" described in Section 14
of the blueprint: confidence, evidence, reasoning, and optional
graph/legal grounding.

Keeping this in one shared dataclass is what makes it possible for the
orchestrator, the citizen UI, and the police console to all render agent
output the same way, no matter which of the ten agents produced it.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class Verdict(str, Enum):
    SAFE = "SAFE"
    CAUTION = "CAUTION"
    DANGEROUS = "DANGEROUS"
    STOP = "STOP"  # used specifically by the UPI agent's proceed/stop decision
    UNKNOWN = "UNKNOWN"


@dataclass
class AgentResponse:
    agent_name: str
    verdict: Verdict
    confidence: float  # 0.0 - 1.0
    evidence: list[str] = field(default_factory=list)
    reasoning: str = ""
    graph_explanation: str | None = None
    supporting_law: str | None = None
    visual_highlight: dict[str, Any] | None = None
    raw_score: float | None = None
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["verdict"] = self.verdict.value
        return d


class BaseAgent:
    """
    Every concrete agent implements `.analyze(payload) -> AgentResponse`.
    This base class exists so the orchestrator can treat all ten agents
    uniformly, and so unit tests can assert every agent returns a
    conformant AgentResponse regardless of internal implementation.
    """

    name: str = "base_agent"

    def analyze(self, payload: dict[str, Any]) -> AgentResponse:  # pragma: no cover
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement analyze()"
        )

    def _response(
        self,
        verdict: Verdict,
        confidence: float,
        evidence: list[str],
        reasoning: str,
        **kwargs: Any,
    ) -> AgentResponse:
        return AgentResponse(
            agent_name=self.name,
            verdict=verdict,
            confidence=round(min(max(confidence, 0.0), 1.0), 4),
            evidence=evidence,
            reasoning=reasoning,
            **kwargs,
        )
