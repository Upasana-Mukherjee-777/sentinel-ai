"""
services/api_gateway/main.py

FastAPI entry point (Blueprint Section 5, "API Gateway" + Section 10,
"API Design"). Run locally with:

    uvicorn services.api_gateway.main:app --reload --port 8000

Then see interactive docs at http://localhost:8000/docs
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.api_gateway.routers import agents

app = FastAPI(
    title="Sentinel AI API",
    description=(
        "AI Digital Crime Prevention Operating System — API Gateway. "
        "See docs/Sentinel_AI_ET_Hackathon_2026_Blueprint.md for the full architecture."
    ),
    version="0.1.0-hackathon-scaffold",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tightened to specific origins before any non-demo deployment
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agents.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "sentinel-ai-api-gateway"}


@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": "Sentinel AI API Gateway is running.",
        "docs": "/docs",
        "health": "/health",
    }
