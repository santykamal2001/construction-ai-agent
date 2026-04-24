"""
Claude-powered RAG agent for construction inspection queries.
Retrieves relevant chunks from vector DB, then uses Claude to answer.
"""
import logging
import statistics
import time
from typing import Optional

import os

import anthropic

from src.config import CLAUDE_MODEL
from src.vector_store import search

logger = logging.getLogger(__name__)

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


def query(
    question: str,
    project_folder: Optional[str] = None,
    n_results: int = 8,
    stream: bool = False
) -> dict:
    """
    RAG query pipeline:
    1. Retrieve relevant chunks from vector DB
    2. Build context prompt
    3. Call Claude API
    4. Return answer with sources
    """
    t_start = time.perf_counter()

    # Step 1: Retrieve — fetch more than needed so deduplication still leaves enough unique content
    chunks = search(question, project_folder=project_folder, n_results=max(n_results * 2, 16))

    if not chunks:
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

    # Step 2: Deduplicate near-identical chunks (e.g. repeated approval stamp templates)
    # Also cap chunks per file so no single document dominates the context.
    MAX_CHUNKS_PER_FILE = 3
    unique_chunks = []
    file_chunk_counts: dict = {}
    for chunk in chunks:
        text = chunk["text"].strip()
        fname = chunk["file_name"]

        if file_chunk_counts.get(fname, 0) >= MAX_CHUNKS_PER_FILE:
            continue

        is_duplicate = any(
            _similarity(text, kept["text"]) > 0.85
            for kept in unique_chunks
        )
        if not is_duplicate:
            unique_chunks.append(chunk)
            file_chunk_counts[fname] = file_chunk_counts.get(fname, 0) + 1

    # Build context from unique chunks only
    context_parts = []
    seen_files = set()
    for chunk in unique_chunks:
        fname = chunk["file_name"]
        score = chunk["relevance_score"]
        context_parts.append(
            f"--- Document: {fname} (relevance: {score}) ---\n{chunk['text']}"
        )
        seen_files.add(fname)

    context = "\n\n".join(context_parts)

    user_message = f"""Based on the following project documents, please answer this question:

QUESTION: {question}

PROJECT DOCUMENTS:
{context}

Please provide a clear, specific answer citing which documents contain the relevant information."""

    # Step 3: Call Claude (read key at call time so sidebar input is picked up)
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))

    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}]
        )
        answer = response.content[0].text
    except anthropic.AuthenticationError:
        answer = "⚠️ API key error. Please set your ANTHROPIC_API_KEY in the .env file."
    except Exception as e:
        logger.error(f"Claude API error: {e}")
        answer = f"Error calling AI model: {str(e)}"

    scores = [c["relevance_score"] for c in unique_chunks]
    latency_ms = int((time.perf_counter() - t_start) * 1000)

    return {
        "answer": answer,
        "sources": [
            {
                "file_name": c["file_name"],
                "file_path": c["file_path"],
                "relevance_score": c["relevance_score"],
                "excerpt": c["text"][:300] + "..." if len(c["text"]) > 300 else c["text"]
            }
            for c in unique_chunks
        ],
        "chunks_used": len(unique_chunks),
        "latency_ms": latency_ms,
        "top_relevance_score": round(max(scores), 3) if scores else 0.0,
        "mean_relevance_score": round(statistics.mean(scores), 3) if scores else 0.0,
        "min_relevance_score": round(min(scores), 3) if scores else 0.0,
        "source_files": list({c["file_name"] for c in unique_chunks}),
    }


def _similarity(a: str, b: str) -> float:
    """Quick Jaccard similarity on word sets — enough to catch near-duplicate template chunks."""
    words_a = set(a.lower().split())
    words_b = set(b.lower().split())
    if not words_a or not words_b:
        return 0.0
    return len(words_a & words_b) / len(words_a | words_b)


def get_project_summary(project_folder: str) -> str:
    """Generate a high-level project summary from indexed documents."""
    result = query(
        "Give me a comprehensive summary of this project including: "
        "project type, location, current condition/status, key findings, "
        "safety concerns, and recommended next actions.",
        project_folder=project_folder,
        n_results=10
    )
    return result["answer"]
