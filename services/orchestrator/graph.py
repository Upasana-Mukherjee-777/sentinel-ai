"""
services/orchestrator/graph.py

The Sentinel Orchestrator (Blueprint Section 7.2). A LangGraph state
machine that implements Workflow 1 (WhatsApp message with an embedded
URL/QR gets handed off to the Fake Website Agent) and Workflow 10
(cross-platform correlation: any DANGEROUS/STOP verdict gets written to
the Fraud Graph so later checks on a related entity inherit the risk).

Blueprint Section 5 explains why LangGraph specifically: explicit state
graphs make every routing decision inspectable and replayable, which
matters both for debugging and for evidentiary integrity if a case ends
up in front of a court. This module is the concrete implementation of
that claim -- every node transition below is logged in `state["trace"]`.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, TypedDict

from langgraph.graph import StateGraph, START, END

from services.agents import (
    CallIntelligenceAgent,
    CounterfeitCurrencyAgent,
    DeepfakeDetectionAgent,
    FakeWebsiteAgent,
    UPIFraudAgent,
    Verdict,
    WhatsAppFraudAgent,
    detect_input_kind,
    to_citizen_message,
)

URL_PATTERN = re.compile(r"https?://[^\s]+")


class OrchestratorState(TypedDict, total=False):
    payload: dict[str, Any]
    input_kind: str
    agent_results: list[dict[str, Any]]
    extracted_url: str | None
    trace: list[str]
    citizen_message: dict[str, Any]
    graph_writes: list[dict[str, Any]]


# Agents are instantiated once and reused across requests -- the ML
# ones (WhatsApp, UPI) train once at import time, not per-request.
_whatsapp_agent = WhatsAppFraudAgent()
_website_agent = FakeWebsiteAgent()
_upi_agent = UPIFraudAgent()
_call_agent = CallIntelligenceAgent()
_currency_agent = CounterfeitCurrencyAgent()
_deepfake_agent = DeepfakeDetectionAgent()


def _hash_entity(value: str) -> str:
    """Matches the hashed-identifier approach in the Postgres schema (data/postgres/schema.sql)."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:32]


def route_node(state: OrchestratorState) -> OrchestratorState:
    kind = detect_input_kind(state["payload"])
    trace = state.get("trace", [])
    trace.append(f"router: classified input as '{kind}'")
    return {**state, "input_kind": kind, "trace": trace, "agent_results": []}


def whatsapp_node(state: OrchestratorState) -> OrchestratorState:
    payload = state["payload"]
    result = _whatsapp_agent.analyze(payload).to_dict()
    trace = state["trace"] + ["whatsapp_fraud_agent: analyzed message text"]

    text = payload.get("text", "") or payload.get("ocr_text", "")
    url_match = URL_PATTERN.search(text)
    extracted_url = url_match.group(0) if url_match else payload.get("qr_decoded_url")

    return {
        **state,
        "agent_results": state["agent_results"] + [result],
        "extracted_url": extracted_url,
        "trace": trace,
    }


def website_followup_node(state: OrchestratorState) -> OrchestratorState:
    """Workflow 1: a URL or QR code found inside a WhatsApp message is
    handed off to the Fake Website Agent automatically."""
    url = state.get("extracted_url")
    trace = state["trace"]
    if not url:
        trace.append("website_followup: no URL/QR found, skipping Fake Website Agent")
        return {**state, "trace": trace}

    result = _website_agent.analyze({"url": url}).to_dict()
    trace.append(f"fake_website_agent: analyzed extracted URL '{url}'")
    return {**state, "agent_results": state["agent_results"] + [result], "trace": trace}


def call_node(state: OrchestratorState) -> OrchestratorState:
    result = _call_agent.analyze(state["payload"]).to_dict()
    trace = state["trace"] + ["call_intelligence_agent: analyzed transcript"]
    return {**state, "agent_results": state["agent_results"] + [result], "trace": trace}


def currency_node(state: OrchestratorState) -> OrchestratorState:
    result = _currency_agent.analyze(state["payload"]).to_dict()
    trace = state["trace"] + ["counterfeit_currency_agent: analyzed image"]
    return {**state, "agent_results": state["agent_results"] + [result], "trace": trace}


def website_direct_node(state: OrchestratorState) -> OrchestratorState:
    result = _website_agent.analyze(state["payload"]).to_dict()
    trace = state["trace"] + ["fake_website_agent: analyzed submitted URL"]
    return {**state, "agent_results": state["agent_results"] + [result], "trace": trace}


def upi_node(state: OrchestratorState) -> OrchestratorState:
    result = _upi_agent.analyze(state["payload"]).to_dict()
    trace = state["trace"] + ["upi_fraud_agent: scored transaction"]
    return {**state, "agent_results": state["agent_results"] + [result], "trace": trace}


def deepfake_node(state: OrchestratorState) -> OrchestratorState:
    result = _deepfake_agent.analyze(state["payload"]).to_dict()
    trace = state["trace"] + ["deepfake_detection_agent: analyzed media (stub, see agent docstring)"]
    return {**state, "agent_results": state["agent_results"] + [result], "trace": trace}


def graph_write_node(state: OrchestratorState) -> OrchestratorState:
    """Workflow 10: any DANGEROUS/STOP verdict is written to the Fraud
    Network Graph so a future, unrelated-looking check on a linked
    entity inherits the elevated risk. Kept as a no-op-with-log here so
    this module can be imported/tested without a live Neo4j connection;
    the API layer (services/api_gateway) wires the real FraudGraphAgent
    in for actual requests."""
    dangerous_results = [
        r for r in state["agent_results"] if r["verdict"] in (Verdict.DANGEROUS.value, Verdict.STOP.value)
    ]
    writes = []
    trace = state["trace"]
    for r in dangerous_results:
        entity_value = state["payload"].get("caller_number") or state["payload"].get("url") \
            or state["payload"].get("receiver_upi_id") or "unidentified_entity"
        writes.append({
            "entity_value_hash": _hash_entity(str(entity_value)),
            "source_agent": r["agent_name"],
            "risk_score": r["confidence"],
        })
    if writes:
        trace.append(f"graph_write: {len(writes)} flag(s) queued for the Fraud Network Graph")
    return {**state, "graph_writes": writes, "trace": trace}


def citizen_format_node(state: OrchestratorState) -> OrchestratorState:
    from services.agents.base import AgentResponse, Verdict as V

    if not state["agent_results"]:
        return state

    # Surface the most severe verdict to the citizen (DANGEROUS/STOP > CAUTION > SAFE > UNKNOWN)
    severity_order = {V.DANGEROUS: 3, V.STOP: 3, V.CAUTION: 2, V.SAFE: 1, V.UNKNOWN: 0}
    most_severe = max(
        state["agent_results"],
        key=lambda r: severity_order.get(V(r["verdict"]), 0),
    )
    response_obj = AgentResponse(
        agent_name=most_severe["agent_name"],
        verdict=V(most_severe["verdict"]),
        confidence=most_severe["confidence"],
        evidence=most_severe["evidence"],
        reasoning=most_severe["reasoning"],
    )
    citizen_message = to_citizen_message(response_obj, language=state["payload"].get("language", "en"))
    return {**state, "citizen_message": citizen_message}


def _route_after_classification(state: OrchestratorState) -> str:
    return state["input_kind"]


def build_orchestrator() -> Any:
    workflow = StateGraph(OrchestratorState)

    workflow.add_node("route", route_node)
    workflow.add_node("whatsapp", whatsapp_node)
    workflow.add_node("website_followup", website_followup_node)
    workflow.add_node("call", call_node)
    workflow.add_node("currency", currency_node)
    workflow.add_node("website", website_direct_node)
    workflow.add_node("upi", upi_node)
    workflow.add_node("deepfake", deepfake_node)
    workflow.add_node("graph_write", graph_write_node)
    workflow.add_node("citizen_format", citizen_format_node)

    workflow.add_edge(START, "route")
    workflow.add_conditional_edges(
        "route",
        _route_after_classification,
        {
            "whatsapp": "whatsapp",
            "call": "call",
            "currency": "currency",
            "website": "website",
            "upi": "upi",
            "deepfake": "deepfake",
            "unknown": "citizen_format",
        },
    )
    workflow.add_edge("whatsapp", "website_followup")  # Workflow 1
    workflow.add_edge("website_followup", "graph_write")
    workflow.add_edge("call", "graph_write")
    workflow.add_edge("currency", "graph_write")
    workflow.add_edge("website", "graph_write")
    workflow.add_edge("upi", "graph_write")
    workflow.add_edge("deepfake", "graph_write")
    workflow.add_edge("graph_write", "citizen_format")
    workflow.add_edge("citizen_format", END)

    return workflow.compile()


sentinel_orchestrator = build_orchestrator()


def run(payload: dict[str, Any]) -> OrchestratorState:
    """Convenience entry point used by the API gateway and tests."""
    return sentinel_orchestrator.invoke({"payload": payload, "trace": []})
