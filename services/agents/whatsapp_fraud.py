"""
services/agents/whatsapp_fraud.py

WhatsApp Fraud Intelligence Agent (Blueprint Section 7.1, Agent #2).

FUNCTIONAL implementation: trains a small TF-IDF + Logistic Regression
classifier on the bundled synthetic scam-message corpus
(ml/training/synthetic_data/whatsapp_messages.csv) and layers a
rule-based scam-template matcher on top for high-precision categories
(fake KYC, fake police/court notices, parcel scams) that are easy to
express as rules and hard to learn from a tiny demo dataset alone.

In production (Blueprint Section 11) this classifier head is swapped for
a fine-tuned MuRIL / XLM-RoBERTa model trained on real, much larger
labeled data, and OCR (Tesseract/PaddleOCR) feeds image/PDF text into
the same pipeline. The interface below is designed so that swap doesn't
require touching the orchestrator or the API layer.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from .base import AgentResponse, BaseAgent, Verdict

DATA_PATH = (
    Path(__file__).resolve().parents[2]
    / "ml"
    / "training"
    / "synthetic_data"
    / "whatsapp_messages.csv"
)

# High-precision rule patterns for scam categories that are easy to name
# and dangerous to miss, even before the ML model is confident.
SCAM_TEMPLATE_RULES: dict[str, list[str]] = {
    "fake_kyc": [
        r"kyc.{0,15}(update|expir|suspend|block)",
        r"pan card.{0,15}(link|update|block)",
        r"account.{0,15}(suspend|block).{0,20}kyc",
    ],
    "fake_government_notice": [
        r"\bcbi\b", r"\bed\b.{0,10}(notice|summon)", r"digital arrest",
        r"court.{0,10}(warrant|summon)", r"customs.{0,10}(duty|hold|seized)",
    ],
    "parcel_scam": [
        r"parcel.{0,20}(hold|customs|pending|seized)",
        r"courier.{0,20}(pay|fee|clear)",
    ],
    "investment_scam": [
        r"guaranteed.{0,10}(return|profit)", r"double your (money|investment)",
        r"trading.{0,10}(group|signal).{0,10}join",
    ],
    "loan_scam": [
        r"instant loan.{0,15}(approv|disburs)", r"loan.{0,10}without.{0,10}document",
    ],
    "job_scam": [
        r"work from home.{0,15}(earn|daily payout)", r"part.?time job.{0,15}(₹|rs\.?)\s?\d+.{0,10}day",
    ],
}

URGENCY_MARKERS = [
    r"\bwithin\s+\d+\s+(hour|min)", r"immediate(ly)?", r"urgent", r"act now",
    r"failure to comply", r"legal action will be taken",
]


class WhatsAppFraudAgent(BaseAgent):
    name = "whatsapp_fraud_agent"

    def __init__(self) -> None:
        self._vectorizer: TfidfVectorizer | None = None
        self._model: LogisticRegression | None = None
        self._compiled_rules = {
            category: [re.compile(p, re.IGNORECASE) for p in patterns]
            for category, patterns in SCAM_TEMPLATE_RULES.items()
        }
        self._urgency_patterns = [re.compile(p, re.IGNORECASE) for p in URGENCY_MARKERS]
        self._train()

    def _train(self) -> None:
        texts: list[str] = []
        labels: list[int] = []
        with open(DATA_PATH, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                texts.append(row["message"])
                labels.append(int(row["is_scam"]))

        self._vectorizer = TfidfVectorizer(
            ngram_range=(1, 2), min_df=1, max_features=4000, sublinear_tf=True
        )
        X = self._vectorizer.fit_transform(texts)
        self._model = LogisticRegression(max_iter=1000, class_weight="balanced")
        self._model.fit(X, labels)

    def _rule_matches(self, text: str) -> dict[str, list[str]]:
        matches: dict[str, list[str]] = {}
        for category, patterns in self._compiled_rules.items():
            hits = [p.pattern for p in patterns if p.search(text)]
            if hits:
                matches[category] = hits
        return matches

    def analyze(self, payload: dict[str, Any]) -> AgentResponse:
        text: str = payload.get("text", "") or payload.get("ocr_text", "")
        if not text.strip():
            return self._response(
                Verdict.UNKNOWN, 0.0, [], "No text content provided to analyze."
            )

        assert self._vectorizer is not None and self._model is not None
        X = self._vectorizer.transform([text])
        ml_scam_prob = float(self._model.predict_proba(X)[0][1])

        rule_hits = self._rule_matches(text)
        urgency_hits = [p.pattern for p in self._urgency_patterns if p.search(text)]

        # Rules provide a high-confidence floor; ML provides generalization
        # to templates the rules don't cover.
        rule_boost = 0.35 if rule_hits else 0.0
        urgency_boost = 0.1 if urgency_hits else 0.0
        fraud_probability = min(1.0, ml_scam_prob + rule_boost + urgency_boost)

        evidence = []
        if rule_hits:
            categories = ", ".join(sorted(rule_hits.keys()))
            evidence.append(f"Matched known scam template categories: {categories}")
        if urgency_hits:
            evidence.append("Contains urgency/pressure language typical of scam messaging")
        evidence.append(f"ML classifier scam probability: {ml_scam_prob:.2f}")

        if fraud_probability >= 0.75:
            verdict = Verdict.DANGEROUS
            reasoning = (
                "This message strongly matches known fraud patterns "
                f"({', '.join(rule_hits.keys()) if rule_hits else 'linguistic scam markers'}). "
                "Do not click links, share OTPs, or make payments."
            )
        elif fraud_probability >= 0.4:
            verdict = Verdict.CAUTION
            reasoning = (
                "This message has some characteristics of fraud messaging. "
                "Verify independently through an official channel before acting on it."
            )
        else:
            verdict = Verdict.SAFE
            reasoning = "No strong fraud indicators detected in this message."

        return self._response(
            verdict,
            fraud_probability,
            evidence,
            reasoning,
            raw_score=fraud_probability,
            visual_highlight={"matched_categories": list(rule_hits.keys())},
        )
