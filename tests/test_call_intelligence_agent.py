from services.agents import CallIntelligenceAgent, Verdict

agent = CallIntelligenceAgent()


def test_digital_arrest_call_flagged_dangerous():
    result = agent.analyze({
        "transcript": "This is CBI. You are under digital arrest, do not disconnect the call, "
                      "transfer money immediately to a safe government account."
    })
    assert result.verdict == Verdict.DANGEROUS


def test_ordinary_call_is_safe():
    result = agent.analyze({"transcript": "Hi, just calling to confirm our meeting tomorrow at 3pm."})
    assert result.verdict == Verdict.SAFE
