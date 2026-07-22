# 🛡️ Sentinel AI
### AI-Powered Digital Crime Prevention Platform
**ET AI Hackathon 2026 – Problem Statement 6**

Sentinel AI is a multi-agent platform designed to help citizens, banks, and law enforcement identify and respond to digital fraud before financial damage occurs.

Instead of relying on a single detection model, Sentinel AI combines specialized AI agents that analyze different fraud scenarios—including phishing websites, WhatsApp scams, suspicious UPI transactions, fraud call transcripts, counterfeit currency images, and crime intelligence—to provide faster and more reliable decisions.

---

# Key Features

- WhatsApp Scam Detection
- Phishing & Fake Website Detection
- UPI Fraud Risk Analysis
- Fraud Call Transcript Analysis
- Fraud Network Graph (Neo4j)
- Police Investigation Copilot
- Crime Heatmap Dashboard
- Citizen Assistance Chat Interface
- Counterfeit Currency Screening
- Modular Deepfake Detection Framework

---

# Technology Stack

**Backend**
- FastAPI
- Python
- LangGraph
- Docker

**Machine Learning**
- Scikit-learn
- Random Forest
- Logistic Regression
- TF-IDF
- OpenCV

**Databases**
- PostgreSQL
- Redis
- Neo4j
- Qdrant

**Frontend**
- HTML
- CSS
- JavaScript

---

# Project Architecture

```
Citizen / Police Portal
          │
          ▼
    FastAPI Gateway
          │
          ▼
   LangGraph Orchestrator
          │
 ┌────────┼────────┐
 │        │        │
WhatsApp Website  UPI
 Agent    Agent   Agent
 │        │        │
 └────────┼────────┘
          ▼
 Fraud Intelligence Layer
          │
    Neo4j Knowledge Graph
```

---

# Repository Structure

```
sentinel-ai/
│
├── services/
│   ├── agents/
│   ├── orchestrator/
│   └── api_gateway/
│
├── frontend/
│
├── docs/
│
├── data/
│
├── tests/
│
└── docker-compose.yml
```

---

# Getting Started

## Clone the repository
```bash
git clone https://github.com/Upasana-Mukherjee-777/sentinel-ai.git
cd sentinel-ai
```

## Run using Docker
```bash
docker compose up
```

## Run locally
```bash
pip install -r requirements.txt
uvicorn services.api_gateway.main:app --reload
```

API documentation:
```
http://localhost:8000/docs
```

---

# Demo Workflows

Sentinel AI currently supports:

- Detecting scam messages shared over WhatsApp
- Identifying suspicious websites
- Assessing risky UPI transactions
- Detecting scam patterns from call transcripts
- Visualizing fraud relationships using Neo4j
- Assisting investigators through a Police Copilot
- Monitoring district-level crime trends
- Performing basic counterfeit currency quality checks

---

# Future Improvements

Some modules are intentionally designed for future expansion:

- Deepfake detection using EfficientNet-based vision models
- Advanced counterfeit currency detection with CNNs
- Live WHOIS and SSL verification
- Production authentication using OAuth2/JWT
- Real-time voice fraud detection

---

# Contributors

**Upasana Mukherjee, Rudranil Chakraborty**
Built for **ET AI Hackathon 2026**.
