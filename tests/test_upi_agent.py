from services.agents import UPIFraudAgent, Verdict

agent = UPIFraudAgent()


def test_high_risk_transaction_recommends_stop():
    result = agent.analyze({
        "amount": 40000,
        "payee_is_new": True,
        "hour_of_day": 23,
        "receiver_account_age_days": 3,
        "receiver_prior_fraud_reports": 3,
    })
    assert result.verdict == Verdict.STOP
    assert any("prior fraud report" in e for e in result.evidence)


def test_low_risk_transaction_is_safe():
    result = agent.analyze({
        "amount": 500,
        "payee_is_new": False,
        "hour_of_day": 14,
        "receiver_account_age_days": 900,
        "receiver_prior_fraud_reports": 0,
    })
    assert result.verdict == Verdict.SAFE
