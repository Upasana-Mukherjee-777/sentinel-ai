from services.agents import Verdict, WhatsAppFraudAgent

agent = WhatsAppFraudAgent()


def test_flags_digital_arrest_scam_as_dangerous():
    result = agent.analyze({
        "text": "This is CBI Cyber Crime Division. Digital arrest warrant issued. "
                "Pay fine immediately to avoid arrest."
    })
    assert result.verdict == Verdict.DANGEROUS
    assert result.confidence > 0.7
    assert any("fake_government_notice" in e for e in result.evidence)


def test_flags_fake_kyc_message():
    result = agent.analyze({
        "text": "Your KYC has expired. Update immediately within 24 hours "
                "or your account will be suspended."
    })
    assert result.verdict in (Verdict.DANGEROUS, Verdict.CAUTION)


def test_benign_message_is_safe():
    result = agent.analyze({"text": "Hey are we still meeting for lunch tomorrow at 1pm?"})
    assert result.verdict == Verdict.SAFE


def test_empty_input_is_unknown():
    result = agent.analyze({"text": ""})
    assert result.verdict == Verdict.UNKNOWN
