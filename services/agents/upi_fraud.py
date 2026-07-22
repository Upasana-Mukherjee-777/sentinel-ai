"""
services/agents/upi_fraud.py

UPI Fraud Intelligence Agent (Blueprint Section 7.1, Agent #5).

FUNCTIONAL implementation: a RandomForest classifier trained on the
bundled synthetic transaction dataset
(ml/training/synthetic_data/upi_transactions.csv), which encodes the
same feature patterns described in the blueprint (Section 11): payee
novelty, amount vs. history, time-of-day anomaly, receiver account age,
and — critically — whether the receiver entity is already flagged in
the Fraud Network Graph.

In production this is trained on real (anonymized, consented) partner
bank data at far greater scale, exactly as described in the blueprint's
roadmap (Section 17, Phase 1: "UPI Fraud Agent with a partner bank
sandbox"), and the graph lookup below is a live Neo4j query rather than
a passed-in flag.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.ensemble import RandomForestClassifier

from .base import AgentResponse, BaseAgent, Verdict

DATA_PATH = (
    Path(__file__).resolve().parents[2]
    / "ml"
    / "training"
    / "synthetic_data"
    / "upi_transactions.csv"
)

FEATURE_COLUMNS = [
    "amount",
    "payee_is_new",
    "hour_of_day",
    "receiver_account_age_days",
    "receiver_prior_fraud_reports",
]


class UPIFraudAgent(BaseAgent):
    name = "upi_fraud_agent"

    def __init__(self) -> None:
        self._model: RandomForestClassifier | None = None
        self._train()

    def _train(self) -> None:
        X_rows: list[list[float]] = []
        y: list[int] = []
        with open(DATA_PATH, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                X_rows.append([float(row[c]) for c in FEATURE_COLUMNS])
                y.append(int(row["is_fraud"]))

        X = np.array(X_rows)
        self._model = RandomForestClassifier(
            n_estimators=200, max_depth=6, class_weight="balanced", random_state=42
        )
        self._model.fit(X, y)

    def _feature_contributions(self, features: list[float]) -> list[str]:
        """
        Lightweight, dependency-free stand-in for SHAP (blueprint Section 11
        specifies SHAP for production). Flags which raw features are in a
        risk-elevating range, so the explanation is still grounded in the
        actual input rather than a generic message.
        """
        amount, payee_is_new, hour_of_day, receiver_age, prior_reports = features
        notes = []
        if prior_reports > 0:
            notes.append(
                f"Receiver already linked to {int(prior_reports)} prior fraud report(s) in the Fraud Graph"
            )
        if payee_is_new and amount > 10000:
            notes.append("First-time payee combined with a high transaction amount")
        if hour_of_day >= 22 or hour_of_day <= 5:
            notes.append("Transaction initiated during an unusual off-hours window")
        if receiver_age < 15:
            notes.append(f"Receiver account is very new ({int(receiver_age)} days old)")
        return notes

    def analyze(self, payload: dict[str, Any]) -> AgentResponse:
        amount = float(payload.get("amount", 0))
        payee_is_new = 1.0 if payload.get("payee_is_new", False) else 0.0
        hour_of_day = float(payload.get("hour_of_day", 12))
        receiver_account_age_days = float(payload.get("receiver_account_age_days", 365))
        receiver_prior_fraud_reports = float(payload.get("receiver_prior_fraud_reports", 0))

        features = [amount, payee_is_new, hour_of_day, receiver_account_age_days, receiver_prior_fraud_reports]

        assert self._model is not None
        fraud_prob = float(self._model.predict_proba(np.array([features]))[0][1])

        evidence = self._feature_contributions(features)
        if not evidence:
            evidence.append("No individual risk-elevating factors identified")
        evidence.append(f"Model risk score: {fraud_prob:.2f}")

        if fraud_prob >= 0.6:
            verdict = Verdict.STOP
            reasoning = "High fraud risk. Recommend stopping this payment and verifying the receiver through an independent channel."
        elif fraud_prob >= 0.3:
            verdict = Verdict.CAUTION
            reasoning = "Moderate fraud risk. Proceed only after verifying the receiver."
        else:
            verdict = Verdict.SAFE
            reasoning = "Low fraud risk based on available signals."

        return self._response(
            verdict, fraud_prob, evidence, reasoning,
            raw_score=fraud_prob,
            graph_explanation=(
                f"Receiver has {int(receiver_prior_fraud_reports)} prior linked fraud report(s) in the Fraud Network Graph"
                if receiver_prior_fraud_reports > 0 else None
            ),
        )
