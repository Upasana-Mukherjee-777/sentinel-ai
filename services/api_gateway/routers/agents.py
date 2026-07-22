"""
services/api_gateway/routers/agents.py

REST endpoints for each individual agent (Blueprint Section 10 API
table), plus the generic /orchestrator/analyze endpoint that runs the
full LangGraph workflow. Each agent is instantiated once at module load
(mirrors the orchestrator's approach) so the ML models train once, not
per-request.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from services.agents import (
    CallIntelligenceAgent,
    CounterfeitCurrencyAgent,
    DeepfakeDetectionAgent,
    FakeWebsiteAgent,
    PoliceCopilotAgent,
    UPIFraudAgent,
    WhatsAppFraudAgent,
)
from services.api_gateway.auth import require_role
from services.api_gateway.schemas import (
    AgentResponseOut,
    CallAnalyzeRequest,
    CaseSummaryRequest,
    CurrencyScanRequest,
    OrchestratorRequest,
    OrchestratorResponse,
    UPIPrecheckRequest,
    WebsiteCheckRequest,
    WhatsAppAnalyzeRequest,
)

router = APIRouter(prefix="/agents", tags=["agents"])

_whatsapp_agent = WhatsAppFraudAgent()
_website_agent = FakeWebsiteAgent()
_upi_agent = UPIFraudAgent()
_call_agent = CallIntelligenceAgent()
_currency_agent = CounterfeitCurrencyAgent()
_deepfake_agent = DeepfakeDetectionAgent()
_copilot_agent = PoliceCopilotAgent()


@router.post("/whatsapp/analyze", response_model=AgentResponseOut)
def analyze_whatsapp(
    req: WhatsAppAnalyzeRequest,
    role: str = Depends(require_role("citizen", "bank_partner", "police", "admin")),
) -> AgentResponseOut:
    result = _whatsapp_agent.analyze(req.model_dump())
    return AgentResponseOut(**result.to_dict())


@router.post("/website/check", response_model=AgentResponseOut)
def check_website(
    req: WebsiteCheckRequest,
    role: str = Depends(require_role("citizen", "bank_partner", "police", "admin")),
) -> AgentResponseOut:
    result = _website_agent.analyze(req.model_dump())
    return AgentResponseOut(**result.to_dict())


@router.post("/upi/precheck", response_model=AgentResponseOut)
def upi_precheck(
    req: UPIPrecheckRequest,
    role: str = Depends(require_role("bank_partner", "admin")),
) -> AgentResponseOut:
    result = _upi_agent.analyze(req.model_dump())
    return AgentResponseOut(**result.to_dict())


@router.post("/call/analyze", response_model=AgentResponseOut)
def analyze_call(
    req: CallAnalyzeRequest,
    role: str = Depends(require_role("citizen", "bank_partner", "police", "admin")),
) -> AgentResponseOut:
    result = _call_agent.analyze(req.model_dump())
    return AgentResponseOut(**result.to_dict())


@router.post("/currency/scan", response_model=AgentResponseOut)
def scan_currency(
    req: CurrencyScanRequest,
    role: str = Depends(require_role("citizen", "bank_partner", "police", "admin")),
) -> AgentResponseOut:
    result = _currency_agent.analyze(req.model_dump())
    return AgentResponseOut(**result.to_dict())


@router.post("/deepfake/analyze", response_model=AgentResponseOut)
def analyze_deepfake(
    payload: dict,
    role: str = Depends(require_role("citizen", "police", "admin")),
) -> AgentResponseOut:
    result = _deepfake_agent.analyze(payload)
    return AgentResponseOut(**result.to_dict())


@router.post("/copilot/case/summary", response_model=AgentResponseOut)
def copilot_case_summary(
    req: CaseSummaryRequest,
    role: str = Depends(require_role("police", "admin")),
) -> AgentResponseOut:
    result = _copilot_agent.analyze(req.model_dump())
    return AgentResponseOut(**result.to_dict())


@router.post("/orchestrator/analyze", response_model=OrchestratorResponse)
def orchestrator_analyze(
    req: OrchestratorRequest,
    role: str = Depends(require_role("citizen", "bank_partner", "police", "admin")),
) -> OrchestratorResponse:
    """Runs the full Sentinel Orchestrator (Blueprint Section 7.2 / Workflow 1
    and Workflow 10) rather than a single agent -- this is the endpoint
    the Citizen App frontend calls."""
    from services.orchestrator.graph import run  # imported lazily to keep module import light

    payload = {k: v for k, v in req.model_dump().items() if v is not None}
    if not payload:
        raise HTTPException(status_code=400, detail="Empty request -- provide at least one field to analyze.")

    state = run(payload)
    return OrchestratorResponse(
        input_kind=state.get("input_kind", "unknown"),
        agent_results=[AgentResponseOut(**r) for r in state.get("agent_results", [])],
        citizen_message=state.get("citizen_message"),
        trace=state.get("trace", []),
    )
