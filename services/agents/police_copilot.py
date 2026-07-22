"""
services/agents/police_copilot.py

Police Copilot (Blueprint Section 7.1, Agent #9).

FUNCTIONAL implementation: a small, real, TF-IDF retrieval index over a
bundled corpus of legal-section snippets (docs/legal_corpus/*.txt --
paraphrased, illustrative summaries of BNS/IT Act provisions relevant to
cyber fraud, NOT verbatim legal text and NOT a substitute for the actual
statute or professional legal advice). Given a case description, it
retrieves the most relevant snippets and drafts a structured case
summary that always cites which snippet it drew from.

In production (Blueprint Section 13) this is a full RAG pipeline: BGE
embeddings, Qdrant vector store, hybrid dense+keyword search over the
complete, officially-sourced BNS/IT Act text and live CERT-In/RBI
advisories, with an LLM generation step instructed to only answer from
retrieved chunks. This demo keeps the same retrieval-then-cite CONTRACT
(never assert a legal claim without a retrieved source) using a
dependency-light TF-IDF retriever so it runs without an LLM API key.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .base import AgentResponse, BaseAgent, Verdict

CORPUS_DIR = Path(__file__).resolve().parents[2] / "docs" / "legal_corpus"


class PoliceCopilotAgent(BaseAgent):
    name = "police_copilot_agent"

    def __init__(self) -> None:
        self._chunks: list[dict[str, str]] = []
        self._vectorizer: TfidfVectorizer | None = None
        self._matrix = None
        self._load_corpus()

    def _load_corpus(self) -> None:
        for path in sorted(CORPUS_DIR.glob("*.txt")):
            text = path.read_text(encoding="utf-8").strip()
            self._chunks.append({"source": path.stem, "text": text})

        if not self._chunks:
            return

        self._vectorizer = TfidfVectorizer(stop_words="english")
        self._matrix = self._vectorizer.fit_transform([c["text"] for c in self._chunks])

    def retrieve(self, query: str, k: int = 3) -> list[dict[str, Any]]:
        if not self._chunks or self._vectorizer is None:
            return []
        query_vec = self._vectorizer.transform([query])
        sims = cosine_similarity(query_vec, self._matrix)[0]
        ranked = sorted(zip(self._chunks, sims), key=lambda x: x[1], reverse=True)
        return [{**chunk, "similarity": float(sim)} for chunk, sim in ranked[:k] if sim > 0.05]

    def analyze(self, payload: dict[str, Any]) -> AgentResponse:
        case_description = payload.get("case_description", "")
        if not case_description.strip():
            return self._response(Verdict.UNKNOWN, 0.0, [], "No case description provided.")

        matches = self.retrieve(case_description, k=payload.get("top_k", 3))

        if not matches:
            return self._response(
                Verdict.UNKNOWN, 0.0,
                ["No relevant legal section found in the bundled demo corpus"],
                "Could not ground a recommendation in the available legal corpus. "
                "Escalate to a human legal reviewer rather than acting on an ungrounded suggestion.",
            )

        evidence = [f"{m['source']} (relevance {m['similarity']:.2f})" for m in matches]
        citations = "; ".join(f"{m['source']}" for m in matches)
        summary_lines = "\n".join(f"- [{m['source']}] {m['text'][:220]}..." for m in matches)

        reasoning = (
            f"Retrieved {len(matches)} relevant section(s) from the legal corpus based on the case description. "
            f"Every recommendation below is grounded in a retrieved source -- nothing here is generated "
            f"without citation.\n\n{summary_lines}"
        )

        return self._response(
            Verdict.CAUTION,  # "CAUTION" here just means "review recommended", not a fraud verdict
            max(m["similarity"] for m in matches),
            evidence,
            reasoning,
            supporting_law=citations,
        )
