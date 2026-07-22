# Sentinel AI — Hackathon Scaffold
### AI Digital Crime Prevention Operating System · ET AI Hackathon 2026, Problem Statement 6

This is a **runnable starter implementation** of the architecture described in
[`docs/Sentinel_AI_ET_Hackathon_2026_Blueprint.md`](docs/Sentinel_AI_ET_Hackathon_2026_Blueprint.md).
It is not a finished production system — it's the honest MVP scope from that
blueprint's Section 17.1, wired together end to end so you have something real
to demo, extend, and build the rest of the roadmap on top of.

## What's actually functional here

| Agent | Status | What it really does |
|---|---|---|
| WhatsApp Fraud Agent | **Functional** | Real TF-IDF + Logistic Regression classifier, trained at startup on the bundled synthetic corpus, plus rule-based scam-template matching |
| Fake Website Agent | **Functional** | Real typosquat detection (Levenshtein distance vs. official domains), suspicious TLD/keyword rules |
| UPI Fraud Agent | **Functional** | Real RandomForest model trained on synthetic transaction data, with feature-level explanations |
| Call Intelligence Agent | **Functional (transcript-based)** | Real pattern-matching over call *transcripts* for digital-arrest scam structure. Does not do live audio/ASR/voice-spoof detection — see the module docstring for what's needed to add that |
| Fraud Network Graph Agent | **Functional** | Real Neo4j Cypher queries (needs `docker compose up neo4j`) |
| Police Copilot | **Functional (lightweight RAG)** | Real TF-IDF retrieval over a small bundled, clearly-disclaimed legal-snippet corpus (`docs/legal_corpus/`) — **not verbatim law**, and not a substitute for checking the actual statute |
| Crime Heatmap Agent | **Functional** | Real district-wise aggregation and trend detection over incident data |
| Citizen Assistant | **Functional** | Real intent routing + plain-language response formatting |
| Counterfeit Currency Agent | **Functional, but scoped down** | Real OpenCV image-quality triage (sharpness/framing/color checks). This is **not** the trained security-feature CNN pipeline from the blueprint — see the module docstring |
| Deepfake Detection Agent | **Stub, honestly** | Returns `UNKNOWN` with a clear docstring on the real pipeline to implement. Faking a detector here would be actively misleading given the harm of a wrong verdict |

The **Sentinel Orchestrator** (`services/orchestrator/graph.py`) is a real
LangGraph state machine that runs Blueprint Workflow 1 (a URL inside a
WhatsApp message is automatically handed off to the Fake Website Agent) and
Workflow 10 (any DANGEROUS/STOP verdict is queued as a Fraud Graph write for
cross-platform correlation). Both are covered by passing tests in `tests/`.

## Quickstart

```bash
# 1. Start the full stack (Postgres, Redis, Neo4j, Qdrant, backend API)
docker compose up

# 2. Seed the Neo4j demo graph (optional, for the Graph Explorer panel)
cat data/neo4j/schema.cypher | docker exec -i sentinel-ai-neo4j-1 cypher-shell -u neo4j -p sentinel_dev_password

# 3. Open the API docs
open http://localhost:8000/docs

# 4. Open the demo frontends (plain static files, no build step)
open frontend/citizen-app/index.html
open frontend/police-console/index.html
```

### Running without Docker (backend only)

```bash
pip install -r requirements.txt --break-system-packages
uvicorn services.api_gateway.main:app --reload --port 8000
```

Agents that don't need Neo4j/Postgres (WhatsApp, Website, UPI, Call, Currency,
Copilot) will work immediately. The Fraud Graph Agent needs a running Neo4j
instance — see `docker-compose.yml`.

### Running the tests

```bash
pytest tests/ -v
```

13 tests cover the five functional core agents plus two full orchestrator
workflows (Workflow 1 and the UPI STOP-payment path with a graph write).

## Repo structure

```
sentinel-ai/
├── services/
│   ├── api_gateway/       # FastAPI app, routers, auth, schemas
│   ├── orchestrator/      # LangGraph state machine (services/orchestrator/graph.py)
│   └── agents/            # The ten agents from Blueprint Section 7.1
├── ml/training/            # Synthetic training data + the training happens
│                            # inline in each agent's __init__ for this demo
├── data/
│   ├── postgres/schema.sql
│   └── neo4j/schema.cypher
├── frontend/
│   ├── citizen-app/        # Single-file demo UI (the "scam radar" screen)
│   └── police-console/     # Single-file demo UI (case queue + graph explorer + copilot)
├── docs/
│   ├── Sentinel_AI_ET_Hackathon_2026_Blueprint.md   # the full design doc
│   └── legal_corpus/       # disclaimed, illustrative legal snippets for the RAG demo
├── infra/
│   ├── docker/Dockerfile.backend
│   └── ci-cd/github-actions.yml
└── tests/
```

## API reference (quick)

Every endpoint requires an `X-Demo-Role` header (`citizen`, `bank_partner`,
`police`, or `admin`) — this is a deliberately simple RBAC stand-in, see
`services/api_gateway/auth.py` for what to swap in before any real deployment.

```bash
curl -X POST http://localhost:8000/agents/orchestrator/analyze \
  -H "Content-Type: application/json" -H "X-Demo-Role: citizen" \
  -d '{"text": "Your KYC has expired, verify at http://onlinesbi-verify-kyc.xyz/login"}'
```

Full interactive spec at `/docs` once the backend is running.

## What to build next

The blueprint's Section 17 roadmap and Section 23.1 ("what would push this to
95+") are the two sections worth reading before extending this. In short, the
highest-leverage next steps are:

1. Swap the Deepfake Agent stub for a real EfficientNet-B4 + DCT model trained on FaceForensics++/DFDC
2. Swap the Counterfeit Currency Agent's quality-triage heuristic for the trained YOLOv8 + per-feature CNN pipeline
3. Load-test the UPI precheck path and publish a real latency number
4. Wire the Fake Website Agent to live WHOIS/SSL lookups (needs outbound network access)
5. Replace the RBAC stub with real OAuth2/JWT
