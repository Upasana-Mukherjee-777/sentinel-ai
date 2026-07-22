"""
services/agents/fake_website.py

Fake Website Intelligence Agent (Blueprint Section 7.1, Agent #4).

FUNCTIONAL implementation using deterministic, explainable signals:
  - Levenshtein similarity of the domain against a curated list of
    official Indian bank/government domains (typosquat detection)
  - Suspicious TLD / subdomain-stuffing heuristics
  - Presence of credential-harvesting keywords in the path/query
  - HTTPS presence (structural signal only; this demo does not make
    live network calls)

In production (Blueprint Section 5/11) this is augmented with live
WHOIS/domain-age lookups, real SSL certificate inspection, a headless
browser render for visual phishing-kit similarity (perceptual hashing),
and JS static analysis. Those require outbound network access and are
called out as TODOs so the interface contract doesn't change when they
are added.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from .base import AgentResponse, BaseAgent, Verdict

# A small curated list of official domains this demo protects.
# In production this list is maintained centrally and versioned.
OFFICIAL_DOMAINS = [
    "onlinesbi.sbi", "sbi.co.in", "hdfcbank.com", "icicibank.com",
    "axisbank.com", "npci.org.in", "uidai.gov.in", "incometax.gov.in",
    "rbi.org.in", "cybercrime.gov.in", "indiapost.gov.in",
]

SUSPICIOUS_KEYWORDS = [
    "verify", "kyc-update", "secure-login", "account-block", "confirm-identity",
    "reactivate", "suspended", "customs-fee",
]

SUSPICIOUS_TLDS = {"xyz", "top", "click", "info", "loan", "work", "fit", "gq", "tk"}


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if len(a) < len(b):
        a, b = b, a
    prev_row = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur_row = [i]
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            cur_row.append(min(prev_row[j] + 1, cur_row[j - 1] + 1, prev_row[j - 1] + cost))
        prev_row = cur_row
    return prev_row[-1]


class FakeWebsiteAgent(BaseAgent):
    name = "fake_website_agent"

    def _closest_official_domain(self, domain: str) -> tuple[str, int]:
        best_domain, best_dist = "", 999
        for official in OFFICIAL_DOMAINS:
            dist = _levenshtein(domain, official)
            if dist < best_dist:
                best_domain, best_dist = official, dist
        return best_domain, best_dist

    def analyze(self, payload: dict[str, Any]) -> AgentResponse:
        url = payload.get("url", "").strip()
        if not url:
            return self._response(Verdict.UNKNOWN, 0.0, [], "No URL provided.")

        if not re.match(r"^https?://", url):
            url = "http://" + url

        parsed = urlparse(url)
        domain = parsed.netloc.lower().split(":")[0]
        path_and_query = f"{parsed.path} {parsed.query}".lower()
        tld = domain.split(".")[-1] if "." in domain else ""
        subdomain_count = domain.count(".")

        evidence: list[str] = []
        risk = 0.0

        is_https = parsed.scheme == "https"
        if not is_https:
            risk += 0.15
            evidence.append("Site does not use HTTPS")

        closest, distance = self._closest_official_domain(domain)
        if domain not in OFFICIAL_DOMAINS and 0 < distance <= 3:
            risk += 0.45
            evidence.append(
                f"Domain '{domain}' is visually/textually very close to official domain "
                f"'{closest}' (edit distance {distance}) — likely typosquat"
            )

        if tld in SUSPICIOUS_TLDS:
            risk += 0.15
            evidence.append(f"Uses a TLD ('.{tld}') commonly abused for phishing/disposable sites")

        if subdomain_count > 3:
            risk += 0.1
            evidence.append("Unusually deep subdomain nesting, often used to obscure the true domain")

        matched_keywords = [kw for kw in SUSPICIOUS_KEYWORDS if kw in path_and_query or kw in domain]
        if matched_keywords:
            risk += 0.15
            evidence.append(f"URL contains credential-harvesting language: {', '.join(matched_keywords)}")

        risk = min(risk, 1.0)

        if not evidence:
            evidence.append("No suspicious structural signals detected in this demo's rule set")

        if risk >= 0.6:
            verdict = Verdict.DANGEROUS
            reasoning = "Multiple strong phishing indicators detected. Do not enter credentials or make payments on this site."
        elif risk >= 0.3:
            verdict = Verdict.CAUTION
            reasoning = "Some suspicious signals detected. Verify the domain independently before proceeding."
        else:
            verdict = Verdict.SAFE
            reasoning = "No strong phishing indicators detected by this demo's rule set."

        return self._response(
            verdict, risk, evidence, reasoning,
            raw_score=risk,
            visual_highlight={"domain": domain, "closest_official_match": closest if distance <= 3 else None},
        )
