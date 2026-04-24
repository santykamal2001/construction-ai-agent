"""
Claude-powered RAG agent — BGE retrieval + cross-encoder reranking + Claude generation.
"""
import logging
import statistics
import time
from typing import Optional

import os
import anthropic

from src.config import CLAUDE_MODEL, RERANKER_MODEL
from src.vector_store import search

logger = logging.getLogger(__name__)

_reranker = None

def _get_reranker():
    global _reranker
    if _reranker is None:
        try:
            from sentence_transformers import CrossEncoder
            _reranker = CrossEncoder(RERANKER_MODEL)
            logger.info(f"Loaded reranker: {RERANKER_MODEL}")
        except Exception as e:
            logger.warning(f"Reranker unavailable: {e}")
            _reranker = False
    return _reranker if _reranker else None


SYSTEM_PROMPT = """You are an expert AI assistant for Distinct Engineering Solutions, Inc., a civil engineering company specializing in construction and design.

You help field inspectors quickly access project information including:
- Past inspection findings and deficiencies
- Project history and current status
- Structural condition ratings
- Recommended repairs and priorities
- Safety issues requiring immediate attention

You answer questions based ONLY on the provided document excerpts from the project files.
Be specific, cite which document/report your information comes from, and highlight any safety-critical items.
If information is not available in the provided context, say so clearly.

IMPORTANT: These documents are scanned/digital inspection forms. Field values often appear on the line AFTER their label (e.g. "DESI Insp.:" on one line, then "Manidhar Boyapati" on the next line; or "Contractor Rep:" followed by "Divyesh, Naseer, Walid"). Read labels and the values that follow them together to extract the correct information.

CRITICAL — DISTINGUISH PERSONNEL ROLES:
- "Document Reviewers" or "Approval Stamp Signers" (names appearing in review/approval boxes, e.g. "Reviewed for general conformance") are NOT project workers — they are office administrators who signed off on submittals. Do NOT list them as people who "worked on" the project.
- "Project Workers" are: DESI Inspectors (e.g. "DESI Insp:" field), Contractor Representatives (e.g. "Contractor Rep:" field), Site Engineers, Foremen, and anyone listed in the body of an inspection report as performing physical work or site inspections.
- When asked "who worked on" a project, list ONLY project workers (inspectors, contractor reps, site personnel), NOT document reviewers/approvers.

Always structure your response clearly with:
- Direct answer to the question
- Source document reference
- Any safety warnings if applicable"""


def _rerank(question: str, chunks: list, top_k: int) -> list:
    """Re-score (query, chunk) pairs with cross-encoder and return top_k."""
    reranker = _get_reranker()
    if not reranker or not chunks:
        return chunks[:top_k]
    try:
        pairs = [(question, c["text"]) for c in chunks]
        scores = reranker.predict(pairs)
        for i, c in enumerate(chunks):
            c["rerank_score"] = float(scores[i])
        ranked = sorted(chunks, key=lambda x: x["rerank_score"], reverse=True)
        return ranked[:top_k]
    except Exception as e:
        logger.warning(f"Reranking failed, using vector order: {e}")
        return chunks[:top_k]


def query(
    question: str,
    project_folder: Optional[str] = None,
    n_results: int = 8,
) -> dict:
    t_start = time.perf_counter()

    # Retrieve 3x candidates for reranker to pick from
    candidates = search(question, project_folder=project_folder, n_results=max(n_results * 3, 24))

    if not candidates:
        return {
            "answer": "No relevant documents found. Please index a project folder first.",
            "sources": [],
            "chunks_used": 0,
            "latency_ms": 0,
            "top_relevance_score": 0.0,
            "mean_relevance_score": 0.0,
            "min_relevance_score": 0.0,
            "source_files": [],
        }

    # Deduplicate near-identical chunks (approval stamp templates etc.)
    MAX_CHUNKS_PER_FILE = 6
    unique: list = []
    file_counts: dict = {}

    for chunk in candidates:
        fname = chunk["file_name"]
        if file_counts.get(fname, 0) >= MAX_CHUNKS_PER_FILE:
            continue
        if any(_similarity(chunk["text"], k["text"]) > 0.85 for k in unique):
            continue
        unique.append(chunk)
        file_counts[fname] = file_counts.get(fname, 0) + 1

    # Rerank with cross-encoder, then keep top n_results
    final_chunks = _rerank(question, unique, top_k=n_results)

    context = "\n\n".join(
        f"--- Document: {c['file_name']} (relevance: {c['relevance_score']}) ---\n{c['text']}"
        for c in final_chunks
    )

    user_message = (
        f"Based on the following project documents, please answer this question:\n\n"
        f"QUESTION: {question}\n\n"
        f"PROJECT DOCUMENTS:\n{context}\n\n"
        f"Please provide a clear, specific answer citing which documents contain the relevant information."
    )

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        answer = response.content[0].text
    except anthropic.AuthenticationError:
        answer = "⚠️ API key error. Set ANTHROPIC_API_KEY in your .env file."
    except Exception as e:
        logger.error(f"Claude API error: {e}")
        answer = f"Error calling AI model: {str(e)}"

    scores = [c["relevance_score"] for c in final_chunks]
    latency_ms = int((time.perf_counter() - t_start) * 1000)

    return {
        "answer": answer,
        "sources": [
            {
                "file_name": c["file_name"],
                "file_path": c["file_path"],
                "relevance_score": c["relevance_score"],
                "excerpt": c["text"][:300] + "..." if len(c["text"]) > 300 else c["text"],
            }
            for c in final_chunks
        ],
        "chunks_used": len(final_chunks),
        "latency_ms": latency_ms,
        "top_relevance_score": round(max(scores), 3) if scores else 0.0,
        "mean_relevance_score": round(statistics.mean(scores), 3) if scores else 0.0,
        "min_relevance_score": round(min(scores), 3) if scores else 0.0,
        "source_files": list({c["file_name"] for c in final_chunks}),
    }


def _similarity(a: str, b: str) -> float:
    words_a = set(a.lower().split())
    words_b = set(b.lower().split())
    if not words_a or not words_b:
        return 0.0
    return len(words_a & words_b) / len(words_a | words_b)


def get_project_summary(project_folder: str) -> str:
    result = query(
        "Give me a comprehensive summary of this project including: "
        "project type, location, current condition/status, key findings, "
        "safety concerns, and recommended next actions.",
        project_folder=project_folder,
        n_results=10,
    )
    return result["answer"]
