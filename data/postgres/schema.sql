-- data/postgres/schema.sql
-- Matches the ER diagram in Blueprint Section 9.
-- Sensitive identifiers are stored hashed (SHA-256, truncated), never
-- raw, per Section 9.1's note on the access-controlled vault pattern.
-- This file only creates the transactional schema; the vault mapping
-- hash -> raw value is intentionally out of scope for this scaffold.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    role VARCHAR(20) NOT NULL CHECK (role IN ('citizen', 'bank_partner', 'police', 'admin')),
    phone_hash VARCHAR(64),
    preferred_language VARCHAR(10) DEFAULT 'en',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    report_type VARCHAR(50) NOT NULL,  -- 'whatsapp' | 'call' | 'currency' | 'website' | 'upi' | 'deepfake'
    agent_output JSONB NOT NULL,       -- the full AgentResponse.to_dict() payload
    risk_score FLOAT NOT NULL CHECK (risk_score >= 0 AND risk_score <= 1),
    district VARCHAR(100),             -- feeds the Crime Heatmap Agent (Section 7.1, Agent #8)
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_reports_risk_created ON reports (risk_score, created_at);
CREATE INDEX idx_reports_district ON reports (district);

CREATE TABLE cases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    report_id UUID REFERENCES reports(id),
    status VARCHAR(20) NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'investigating', 'closed', 'escalated')),
    assigned_officer VARCHAR(100),
    recommended_sections TEXT,          -- Police Copilot output (Section 7.1, Agent #9)
    opened_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE evidence (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    case_id UUID REFERENCES cases(id) ON DELETE CASCADE,
    evidence_type VARCHAR(30) NOT NULL,  -- 'call_recording' | 'screenshot' | 'currency_image' | 'transcript'
    storage_url TEXT NOT NULL,
    chain_of_custody_hash VARCHAR(64) NOT NULL
);

-- Relational mirror of the Neo4j graph (Section 9.1). Neo4j remains the
-- source of truth for traversal queries; this table supports fast
-- transactional lookups and joins with cases/reports.
CREATE TABLE entities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_type VARCHAR(30) NOT NULL,  -- PhoneNumber | BankAccount | UpiId | Website | Device | Victim | IpAddress | Email
    entity_value_hash VARCHAR(64) NOT NULL UNIQUE,
    aggregate_risk_score FLOAT NOT NULL DEFAULT 0
);

CREATE UNIQUE INDEX idx_entities_type_hash ON entities (entity_type, entity_value_hash);

CREATE TABLE entity_links (
    source_entity_id UUID REFERENCES entities(id),
    target_entity_id UUID REFERENCES entities(id),
    relation_type VARCHAR(50) NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (source_entity_id, target_entity_id, relation_type)
);

CREATE TABLE case_entities (
    case_id UUID REFERENCES cases(id) ON DELETE CASCADE,
    entity_id UUID REFERENCES entities(id),
    PRIMARY KEY (case_id, entity_id)
);
