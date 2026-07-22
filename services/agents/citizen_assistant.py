"""
services/agents/citizen_assistant.py

Citizen Assistant (Blueprint Section 7.1, Agent #10).

FUNCTIONAL implementation: a lightweight intent classifier (rule-based,
deliberately simple and auditable) that looks at what a citizen typed
or uploaded and decides which specialist agent should handle it, then
reformats that agent's AgentResponse into a short, plain-language
message suitable for someone reading it mid-scam under stress
(blueprint Section 15 UX principle: "large text, minimal jargon, single
primary action").

In production (Blueprint Section 11) the intent-routing step is handled
by IndicTrans-based language detection + a small classifier, and the
response-formatting step uses the same LLM backbone as the Police
Copilot with a citizen-facing persona layer. This demo keeps the exact
same TWO-STEP shape (route -> reformat) so that swap is additive, not
a rewrite.
"""

from __future__ import annotations

from typing import Any

from .base import AgentResponse, Verdict

PLAIN_LANGUAGE_ACTION = {
    Verdict.DANGEROUS: "Do not proceed. Do not pay, click, or share any details.",
    Verdict.STOP: "Stop this payment and verify the receiver independently first.",
    Verdict.CAUTION: "Be careful. Verify this independently before you act on it.",
    Verdict.SAFE: "No strong danger signs found, but stay alert.",
    Verdict.UNKNOWN: "We could not check this fully. When in doubt, do not proceed.",
}


def detect_input_kind(payload: dict[str, Any]) -> str:
    """Deliberately simple, auditable routing rules -- see module docstring."""
    if payload.get("transcript"):
        return "call"
    if payload.get("url"):
        return "website"
    if payload.get("image_path") and payload.get("input_type") == "currency":
        return "currency"
    if payload.get("image_path") or payload.get("video_path") or payload.get("audio_path"):
        return "deepfake"
    if payload.get("amount") is not None:
        return "upi"
    if payload.get("text") or payload.get("ocr_text"):
        return "whatsapp"
    return "unknown"


def to_citizen_message(agent_response: AgentResponse, language: str = "en") -> dict[str, Any]:
    """
    Reformats any agent's AgentResponse into the compact, plain-language
    shape the Citizen App frontend renders (Blueprint Section 15).
    Language parameter is accepted for interface completeness; in this
    demo only English strings are produced -- production routes through
    an IndicTrans translation step for Hindi/Bengali (Section 11).
    """
    verdict = agent_response.verdict
    return {
        "headline": verdict.value,
        "action": PLAIN_LANGUAGE_ACTION.get(verdict, "When in doubt, do not proceed."),
        "why": agent_response.reasoning,
        "details": agent_response.evidence,
        "confidence_pct": round(agent_response.confidence * 100),
        "handled_by": agent_response.agent_name,
        "language": language,
    }
