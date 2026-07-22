from services.agents import FakeWebsiteAgent, Verdict

agent = FakeWebsiteAgent()


def test_official_domain_is_safe():
    result = agent.analyze({"url": "https://sbi.co.in"})
    assert result.verdict == Verdict.SAFE


def test_suspicious_tld_and_keywords_flagged():
    result = agent.analyze({"url": "http://account-block-verify.xyz/secure-login"})
    assert result.verdict in (Verdict.CAUTION, Verdict.DANGEROUS)
    assert result.confidence > 0.2
