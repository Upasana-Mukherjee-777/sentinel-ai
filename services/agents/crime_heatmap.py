"""
services/agents/crime_heatmap.py

Crime Heatmap Agent (Blueprint Section 7.1, Agent #8).

FUNCTIONAL implementation: aggregates a list of incident reports
(district, category, timestamp -- as would be read from the `reports`
Postgres table in production) into district-wise counts and a simple
trend signal (rate of change over the trailing window vs. the window
before it). This is a genuine, working aggregation and forecast-signal
computation; it does not fabricate geodata.

In production (Blueprint Section 7.1 / 17) this is fed by real,
consented, geotagged reports at scale and the trend signal is replaced
by the Prophet/spatial-ARIMA forecasting model named in Section 11 --
the interface (a list of {district, count, trend} rows) stays the same
so the frontend heatmap component doesn't need to change when the
forecasting model is swapped in.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from .base import AgentResponse, BaseAgent, Verdict


class CrimeHeatmapAgent(BaseAgent):
    name = "crime_heatmap_agent"

    def aggregate(self, incidents: list[dict[str, Any]], window_days: int = 7) -> list[dict[str, Any]]:
        now = datetime.now(timezone.utc)
        current_window_start = now - timedelta(days=window_days)
        prior_window_start = now - timedelta(days=window_days * 2)

        current_counts: dict[str, int] = defaultdict(int)
        prior_counts: dict[str, int] = defaultdict(int)

        for incident in incidents:
            district = incident.get("district", "unknown")
            ts = incident.get("timestamp")
            if isinstance(ts, str):
                ts = datetime.fromisoformat(ts)
            if ts is None:
                continue
            if ts >= current_window_start:
                current_counts[district] += 1
            elif ts >= prior_window_start:
                prior_counts[district] += 1

        results = []
        for district in sorted(set(current_counts) | set(prior_counts)):
            current = current_counts.get(district, 0)
            prior = prior_counts.get(district, 0)
            if prior == 0:
                trend = "new_hotspot" if current > 0 else "stable"
            else:
                pct_change = (current - prior) / prior
                trend = "rising" if pct_change > 0.25 else "falling" if pct_change < -0.25 else "stable"
            results.append({"district": district, "current_count": current, "prior_count": prior, "trend": trend})

        return sorted(results, key=lambda r: r["current_count"], reverse=True)

    def analyze(self, payload: dict[str, Any]) -> AgentResponse:
        incidents = payload.get("incidents", [])
        window_days = payload.get("window_days", 7)
        aggregated = self.aggregate(incidents, window_days)

        rising = [r for r in aggregated if r["trend"] in ("rising", "new_hotspot")]
        evidence = [
            f"{r['district']}: {r['current_count']} incidents in last {window_days}d ({r['trend']})"
            for r in aggregated[:5]
        ] or ["No incident data available for this window"]

        verdict = Verdict.CAUTION if rising else Verdict.SAFE
        reasoning = (
            f"{len(rising)} district(s) showing rising or newly-emerging incident trends over the last {window_days} days."
            if rising else "No districts showing a significant rising trend in this window."
        )

        return self._response(
            verdict, 0.5 if rising else 0.1, evidence, reasoning,
            visual_highlight={"districts": aggregated},
        )
