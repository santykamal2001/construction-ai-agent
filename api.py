"""
DEST AI Inspector — FastAPI backend
Exposes RAG pipeline to the React frontend.
Run: uvicorn api:app --port 8000 --reload
"""
import json
import os
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import sys
sys.path.insert(0, str(Path(__file__).parent))

from src import database, vector_store
from src.database import get_project_stats, get_query_history, get_query_metrics_summary
from src.processor import get_available_projects, process_project

database.init_db()

app = FastAPI(title="DEST AI Inspector API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SAMPLE_DATA_PATH = str(Path(__file__).parent / "sample_data")


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status": "ok",
        "api_connected": bool(os.getenv("ANTHROPIC_API_KEY")),
    }


# ── Projects ──────────────────────────────────────────────────────────────────

@app.get("/projects")
def list_projects():
    projects = get_available_projects(SAMPLE_DATA_PATH)
    result = []
    for p in projects:
        try:
            stats = get_project_stats(p.name)
            result.append({
                "name": p.name,
                "files": stats.get("total", 0),
                "chunks": stats.get("total_chunks", 0),
                "done": stats.get("done", 0),
                "failed": stats.get("failed", 0),
            })
        except Exception:
            result.append({"name": p.name, "files": 0, "chunks": 0, "done": 0, "failed": 0})
    return result


# ── Indexing ──────────────────────────────────────────────────────────────────

class IndexRequest(BaseModel):
    force: bool = False


@app.post("/index/{project_name}")
def index_project(project_name: str, req: IndexRequest):
    projects = get_available_projects(SAMPLE_DATA_PATH)
    proj_path = next((str(p) for p in projects if p.name == project_name), None)
    if not proj_path:
        raise HTTPException(status_code=404, detail=f"Project '{project_name}' not found")

    if req.force:
        for fp in database.get_project_file_paths(project_name):
            vector_store.delete_file_chunks(fp)
        database.reset_project_hashes(project_name)

    stats = process_project(proj_path)
    return {"status": "done", **stats}


# ── Query ─────────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    question: str
    project: str
    n_results: int = 8


@app.post("/query")
def query_endpoint(req: QueryRequest):
    from src.agent import query
    result = query(req.question, project_folder=req.project, n_results=req.n_results)

    safety_flag = any(
        w in result["answer"].lower()
        for w in ["safety", "immediate", "priority 1", "hazard", "danger", "urgent"]
    )
    try:
        database.log_query(
            project_folder=req.project,
            question=req.question,
            answer_preview=result["answer"][:300],
            chunks_used=result["chunks_used"],
            top_score=result["top_relevance_score"],
            mean_score=result["mean_relevance_score"],
            min_score=result["min_relevance_score"],
            source_files=result["source_files"],
            latency_ms=result["latency_ms"],
            had_safety=safety_flag,
        )
    except Exception:
        pass

    result["safety"] = safety_flag
    return result


# ── Documents ─────────────────────────────────────────────────────────────────

@app.get("/documents/{project_name}")
def list_documents(project_name: str):
    try:
        with database.get_connection() as conn:
            rows = conn.execute(
                """SELECT file_name, extension, file_size, status, chunk_count, processed_at
                   FROM files WHERE project_folder = ? ORDER BY chunk_count DESC""",
                (project_name,),
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []


# ── Stats ─────────────────────────────────────────────────────────────────────

@app.get("/stats/{project_name}")
def get_stats(project_name: str):
    return get_project_stats(project_name)


# ── Analytics ─────────────────────────────────────────────────────────────────

@app.get("/analytics/{project_name}")
def get_analytics(project_name: str):
    stats = get_project_stats(project_name)
    summary = get_query_metrics_summary(project_name)
    history = get_query_history(project_name, limit=200)

    # File type breakdown
    try:
        with database.get_connection() as conn:
            rows = conn.execute(
                "SELECT extension, SUM(chunk_count) as cnt FROM files WHERE project_folder=? GROUP BY extension",
                (project_name,),
            ).fetchall()
        type_dist = [
            {"name": (r["extension"] or "").upper().lstrip("."), "value": int(r["cnt"] or 0)}
            for r in rows if r["cnt"]
        ]
    except Exception:
        type_dist = []

    # Most-cited source files
    all_files: list = []
    for row in history:
        try:
            all_files.extend(json.loads(row.get("source_files") or "[]"))
        except Exception:
            pass
    top_files = [{"document": f, "citations": c} for f, c in Counter(all_files).most_common(8)]

    # Query timeline
    query_history = [
        {
            "time": row.get("asked_at", 0),
            "question": (row.get("question") or "")[:80],
            "score": row.get("mean_relevance_score", 0),
            "latency": row.get("latency_ms", 0),
        }
        for row in history
    ]

    return {
        "stats": stats,
        "summary": {
            "total_queries": int(summary.get("total_queries") or 0),
            "avg_relevance": float(summary.get("avg_relevance") or 0),
            "avg_latency": float(summary.get("avg_latency_ms") or 0),
            "safety_count": int(summary.get("safety_count") or 0),
        },
        "type_dist": type_dist,
        "top_files": top_files,
        "query_history": query_history,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
