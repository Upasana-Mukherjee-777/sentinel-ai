"""
services/agents/call_intelligence.py

Call Intelligence Agent (Blueprint Section 7.1, Agent #1).

FUNCTIONAL implementation operating on a text TRANSCRIPT of a call. This
is an honest, scoped-down stand-in for the full pipeline described in
the blueprint (Section 11): live audio -> Whisper ASR -> SpeechBrain
anti-spoofing/AI-voice detection -> this same intent/script analysis.

Rationale for this scope choice (see blueprint Section 17.1, "honest MVP
scope"): live audio streaming and voice-spoof detection need real audio
model weights and a streaming pipeline that a hackathon scaffold cannot
responsibly fake. The scam-SCRIPT analysis below, on transcript text, is
the part of the pipeline that is fully real today, and it is the exact
same intent-classification logic that runs downstream of Whisper in
production — swapping in real ASR later does not change this module's
interface.
"""

from __future__ import annotations

import re
from typing import Any

from .base import AgentResponse, BaseAgent, Verdict

AUTHORITY_IMPERSONATION = [
    r"\bcbi\b", r"\bed\b", r"\bnarcotics\b", r"\btrai\b", r"cyber crime (cell|branch|department)",
    r"income tax department", r"customs department", r"reserve bank of india", r"\brbi\b",
    r"supreme court", r"high court", r"police (department|station|headquarters)",
]

DIGITAL_ARREST_MARKERS = [
    r"digital arrest", r"do not disconnect", r"stay on (this |the )?(call|video)",
    r"house arrest", r"under surveillance", r"cannot leave your (house|home)",
    r"video call.{0,15}(verification|investigation)",
]

PAYMENT_PRESSURE = [
    r"transfer.{0,15}(immediately|now|urgent)", r"pay.{0,15}(fine|penalty|bail)",
    r"send money to.{0,15}(safe|government|verification) account",
    r"share.{0,10}(otp|one time password)", r"share your (bank|account) details",
]

ISOLATION_TACTICS = [
    r"do not tell (anyone|your family)", r"keep this confidential",
    r"this is a secret investigation", r"do not disconnect the call",
]


class CallIntelligenceAgent(BaseAgent):
    name = "call_intelligence_agent"

    def __init__(self) -> None:
        self._authority = [re.compile(p, re.IGNORECASE) for p in AUTHORITY_IMPERSONATION]
        self._arrest = [re.compile(p, re.IGNORECASE) for p in DIGITAL_ARREST_MARKERS]
        self._payment = [re.compile(p, re.IGNORECASE) for p in PAYMENT_PRESSURE]
        self._isolation = [re.compile(p, re.IGNORECASE) for p in ISOLATION_TACTICS]

    def _hits(self, patterns: list[re.Pattern], text: str) -> list[str]:
        return [p.pattern for p in patterns if p.search(text)]

    def analyze(self, payload: dict[str, Any]) -> AgentResponse:
        transcript = payload.get("transcript", "")
        if not transcript.strip():
            return self._response(Verdict.UNKNOWN, 0.0, [], "No transcript provided.")

        authority_hits = self._hits(self._authority, transcript)
        arrest_hits = self._hits(self._arrest, transcript)
        payment_hits = self._hits(self._payment, transcript)
        isolation_hits = self._hits(self._isolation, transcript)

        # Weighted scoring: the combination of authority impersonation +
        # payment pressure is the strongest signal (this is the digital
        # arrest scam's core mechanism), each individually is weaker.
        score = 0.0
        evidence: list[str] = []

        if authority_hits:
            score += 0.3
            evidence.append(f"Caller claims affiliation with an authority: {authority_hits[0]}")
        if arrest_hits:
            score += 0.3
            evidence.append("Uses 'digital arrest' / forced video-surveillance language — no Indian law enforcement agency conducts arrests over a call")
        if payment_hits:
            score += 0.25
            evidence.append(f"Demands payment or sensitive credentials during the call: {payment_hits[0]}")
        if isolation_hits:
            score += 0.15
            evidence.append("Instructs the victim to stay silent or not disconnect — a common isolation tactic")

        if authority_hits and payment_hits:
            score = min(1.0, score + 0.15)  # combination is the core scam pattern
            evidence.append("Combination of authority impersonation + payment demand strongly matches known digital arrest scam structure")

        score = min(score, 1.0)

        if score >= 0.6:
            verdict = Verdict.DANGEROUS
            reasoning = (
                "This call strongly matches the structure of a digital arrest / impersonation scam. "
                "No genuine Indian law enforcement or government agency conducts arrests, investigations, "
                "or demands payment over a phone or video call. Disconnect and verify independently."
            )
        elif score >= 0.3:
            verdict = Verdict.CAUTION
            reasoning = "Some characteristics of scam calls detected. Do not share OTPs or make payments; verify the caller's identity independently."
        else:
            verdict = Verdict.SAFE
            reasoning = "No strong scam-call indicators detected in this transcript."
            if not evidence:
                evidence.append("No authority-impersonation, arrest, payment-pressure, or isolation language detected")

        return self._response(
            verdict, score, evidence, reasoning,
            raw_score=score,
            visual_highlight={
                "authority_impersonation": bool(authority_hits),
                "digital_arrest_language": bool(arrest_hits),
                "payment_pressure": bool(payment_hits),
                "isolation_tactics": bool(isolation_hits),
            },
        )
