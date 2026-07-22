// data/neo4j/schema.cypher
// Constraints and indexes for the Fraud Network Graph (Blueprint Section 7.1, Agent #7).
// Run this once against a fresh Neo4j instance, e.g.:
//   cat data/neo4j/schema.cypher | cypher-shell -u neo4j -p sentinel_dev_password

// Every flagged entity (PhoneNumber, BankAccount, UpiId, Website, Device,
// Victim, IpAddress, Email) is stored as a generic :Entity node with a
// `type` property, rather than one label per type -- this keeps
// FraudGraphAgent's Cypher queries (services/agents/fraud_graph.py)
// uniform across entity types instead of needing a UNION query per type.

CREATE CONSTRAINT entity_value_hash_unique IF NOT EXISTS
FOR (e:Entity) REQUIRE e.value_hash IS UNIQUE;

CREATE INDEX entity_type_idx IF NOT EXISTS
FOR (e:Entity) ON (e.type);

CREATE INDEX entity_risk_score_idx IF NOT EXISTS
FOR (e:Entity) ON (e.aggregate_risk_score);

CREATE INDEX report_created_idx IF NOT EXISTS
FOR (r:Report) ON (r.created_at);

// Example seed data for local demo/testing purposes only.
// Run manually if you want the Graph Explorer UI to have something to show.
MERGE (phone:Entity {value_hash: "demo_phone_hash_001", type: "PhoneNumber"})
  ON CREATE SET phone.aggregate_risk_score = 0.82, phone.first_seen = datetime();
MERGE (upi:Entity {value_hash: "demo_upi_hash_001", type: "UpiId"})
  ON CREATE SET upi.aggregate_risk_score = 0.79, upi.first_seen = datetime();
MERGE (phone)-[l:LINKED {relation_type: "REGISTERED_WITH"}]->(upi)
  ON CREATE SET l.observed_at = datetime();
