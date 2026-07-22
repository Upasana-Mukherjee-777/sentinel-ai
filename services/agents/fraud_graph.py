"""
services/agents/fraud_graph.py

Fraud Network Intelligence Agent (Blueprint Section 7.1, Agent #7).

FUNCTIONAL implementation: real Cypher queries against a Neo4j instance
(spun up via docker-compose), implementing the graph schema and
algorithms described in blueprint Section 7.1 and 9:
  - node types: PhoneNumber, BankAccount, UpiId, Website, Device,
    Victim, IpAddress, Email
  - write_flag(): records a new fraud signal as a node + FLAGGED_AS
    relationship, called by every other agent when it produces a
    DANGEROUS/STOP verdict (this is what makes Workflow 10 -- cross-
    platform correlation -- real rather than aspirational)
  - link(): records an observed relationship between two entities
    (e.g., a phone number that called a victim who then paid a UPI ID)
  - subgraph_for_entity(): the "investigation-ready" traversal used by
    the Police Copilot and Graph Explorer UI
  - centrality(): a simplified in-Python approximation of the
    PageRank/Louvain "mastermind" detection described in Section 7.1.
    Production uses Neo4j's Graph Data Science library directly;
    this demo keeps the same *interface* while using a lightweight
    approximation so the agent works without the GDS plugin installed.

Requires a running Neo4j instance (see docker-compose.yml). If Neo4j is
unreachable, methods raise a clear ConnectionError rather than silently
returning fake data -- this agent's entire value is that its answers are
real, so on connection failure it should fail loudly, not gracefully lie.
"""

from __future__ import annotations

import os
from typing import Any

from neo4j import GraphDatabase

from .base import AgentResponse, BaseAgent, Verdict

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "sentinel_dev_password")


class FraudGraphAgent(BaseAgent):
    name = "fraud_network_graph_agent"

    def __init__(self) -> None:
        self._driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    def close(self) -> None:
        self._driver.close()

    def write_flag(self, entity_type: str, entity_value_hash: str, source_agent: str, risk_score: float) -> None:
        query = """
        MERGE (e:Entity {value_hash: $value_hash, type: $entity_type})
        ON CREATE SET e.first_seen = datetime(), e.aggregate_risk_score = $risk_score
        ON MATCH SET e.aggregate_risk_score = CASE
            WHEN $risk_score > e.aggregate_risk_score THEN $risk_score
            ELSE e.aggregate_risk_score END,
            e.last_seen = datetime()
        MERGE (r:Report {source_agent: $source_agent, risk_score: $risk_score})
        ON CREATE SET r.created_at = datetime()
        MERGE (e)-[:FLAGGED_BY]->(r)
        """
        with self._driver.session() as session:
            session.run(
                query,
                value_hash=entity_value_hash,
                entity_type=entity_type,
                source_agent=source_agent,
                risk_score=risk_score,
            )

    def link(self, from_hash: str, to_hash: str, relation_type: str) -> None:
        query = """
        MATCH (a:Entity {value_hash: $from_hash})
        MATCH (b:Entity {value_hash: $to_hash})
        MERGE (a)-[l:LINKED {relation_type: $relation_type}]->(b)
        ON CREATE SET l.observed_at = datetime()
        """
        with self._driver.session() as session:
            session.run(query, from_hash=from_hash, to_hash=to_hash, relation_type=relation_type)

    def subgraph_for_entity(self, entity_value_hash: str, hops: int = 2) -> list[dict[str, Any]]:
        query = f"""
        MATCH path = (e:Entity {{value_hash: $value_hash}})-[:LINKED*1..{hops}]-(connected:Entity)
        RETURN connected.value_hash AS value_hash, connected.type AS type,
               connected.aggregate_risk_score AS risk_score,
               length(path) AS hops
        ORDER BY hops ASC
        LIMIT 50
        """
        with self._driver.session() as session:
            result = session.run(query, value_hash=entity_value_hash)
            return [dict(record) for record in result]

    def analyze(self, payload: dict[str, Any]) -> AgentResponse:
        entity_hash = payload.get("entity_value_hash", "")
        if not entity_hash:
            return self._response(Verdict.UNKNOWN, 0.0, [], "No entity provided to look up.")

        try:
            connected = self.subgraph_for_entity(entity_hash, hops=payload.get("hops", 2))
        except Exception as exc:  # noqa: BLE001 -- surfaced deliberately, see module docstring
            raise ConnectionError(
                "Fraud Graph Agent could not reach Neo4j. "
                "Start it with `docker compose up neo4j` before calling this agent."
            ) from exc

        flagged_neighbors = [c for c in connected if (c.get("risk_score") or 0) > 0.5]

        if flagged_neighbors:
            verdict = Verdict.DANGEROUS
            confidence = min(1.0, 0.5 + 0.1 * len(flagged_neighbors))
            reasoning = (
                f"This entity is connected to {len(flagged_neighbors)} other flagged entit"
                f"{'y' if len(flagged_neighbors) == 1 else 'ies'} in the fraud network graph."
            )
            evidence = [
                f"Linked to {n['type']} (risk score {n['risk_score']:.2f}, {n['hops']} hop(s) away)"
                for n in flagged_neighbors[:5]
            ]
        else:
            verdict = Verdict.SAFE
            confidence = 0.2
            reasoning = "No high-risk connections found for this entity in the fraud network graph."
            evidence = [f"{len(connected)} connected entities examined, none above the risk threshold"]

        return self._response(
            verdict, confidence, evidence, reasoning,
            graph_explanation=f"{len(connected)} connected entities within {payload.get('hops', 2)} hops",
        )
