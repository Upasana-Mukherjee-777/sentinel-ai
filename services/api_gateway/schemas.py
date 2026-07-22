"""
services/api_gateway/schemas.py

Pydantic request/response models for the API surface described in
Blueprint Section 10. `AgentResponseOut` mirrors the AgentResponse
dataclass in services/agents/base.py exactly -- this is what makes
every /agents/* endpoint return the same shape regardless of which
of the ten agents handled the request.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AgentResponseOut(BaseModel):
    agent_name: str
    verdict: str
    confidence: float
    evidence: list[str] = Field(default_factory=list)
    reasoning: str
    graph_explanation: str | None = None
    supporting_law: str | None = None
    visual_highlight: dict[str, Any] | None = None
    raw_score: float | None = None
    generated_at: str


class WhatsAppAnalyzeRequest(BaseModel):
    text: str | None = None
    ocr_text: str | None = None


class WebsiteCheckRequest(BaseModel):
    url: str


class UPIPrecheckRequest(BaseModel):
    receiver_upi_id: str
    amount: float
    payee_is_new: bool = False
    hour_of_day: int = Field(default=12, ge=0, le=23)
    receiver_account_age_days: float = 365
    receiver_prior_fraud_reports: int = 0


class CallAnalyzeRequest(BaseModel):
    transcript: str
    caller_number: str | None = None


class CurrencyScanRequest(BaseModel):
    image_path: str


class CaseSummaryRequest(BaseModel):
    case_description: str
    top_k: int = 3


class OrchestratorRequest(BaseModel):
    """Generic entry point mirroring the orchestrator's routing logic --
    submit any citizen input and let the Sentinel Orchestrator classify
    and route it (Blueprint Section 7.2)."""

    text: str | None = None
    transcript: str | None = None
    url: str | None = None
    image_path: str | None = None
    caller_number: str | None = None
    amount: float | None = None
    payee_is_new: bool | None = None
    hour_of_day: int | None = None
    receiver_account_age_days: float | None = None
    receiver_prior_fraud_reports: int | None = None
    language: str = "en"


class OrchestratorResponse(BaseModel):
    input_kind: str
    agent_results: list[AgentResponseOut]
    citizen_message: dict[str, Any] | None = None
    trace: list[str]
