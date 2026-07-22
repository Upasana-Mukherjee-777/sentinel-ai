from services.orchestrator.graph import run


def test_whatsapp_with_url_triggers_website_followup_workflow_1():
    """Blueprint Workflow 1: a URL inside a WhatsApp message is automatically
    handed off to the Fake Website Agent by the orchestrator."""
    state = run({
        "text": "Your KYC has expired, verify at http://onlinesbi-verify-kyc.xyz/login"
    })
    agent_names = [r["agent_name"] for r in state["agent_results"]]
    assert "whatsapp_fraud_agent" in agent_names
    assert "fake_website_agent" in agent_names
    assert state["citizen_message"]["headline"] in ("DANGEROUS", "CAUTION")


def test_upi_precheck_workflow_writes_graph_flag_on_high_risk():
    state = run({
        "amount": 40000,
        "payee_is_new": True,
        "hour_of_day": 23,
        "receiver_account_age_days": 3,
        "receiver_prior_fraud_reports": 3,
    })
    assert state["citizen_message"]["headline"] == "STOP"
    assert len(state.get("graph_writes", [])) == 1


def test_unrecognized_input_routes_to_unknown():
    state = run({})
    assert state["input_kind"] == "unknown"
