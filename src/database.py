"""
SQLite metadata store for file tracking.
Tracks: file path, hash, status, timestamps, error logs, and query history.
"""
import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Optional

from src.config import SQLITE_PATH


def get_connection() -> sqlite3.Connection:
    SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(SQLITE_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE NOT NULL,
                file_name TEXT NOT NULL,
                project_folder TEXT NOT NULL,
                file_size INTEGER,
                file_hash TEXT,
                extension TEXT,
                status TEXT DEFAULT 'pending',
                error_message TEXT,
                chunk_count INTEGER DEFAULT 0,
                created_at REAL,
                updated_at REAL,
                processed_at REAL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON files(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_project ON files(project_folder)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_hash ON files(file_hash)")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS query_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_folder TEXT NOT NULL,
                question TEXT NOT NULL,
                answer_preview TEXT,
                chunks_used INTEGER,
                top_relevance_score REAL,
                mean_relevance_score REAL,
                min_relevance_score REAL,
                source_files TEXT,
                latency_ms INTEGER,
                had_safety_flag INTEGER DEFAULT 0,
                asked_at REAL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_qlog_project ON query_log(project_folder)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_qlog_asked_at ON query_log(asked_at)")
        conn.commit()


def register_file(file_path: str, project_folder: str, file_size: int, extension: str) -> int:
    """Register a file in the DB. Returns file_id."""
    path = Path(file_path)
    now = time.time()
    with get_connection() as conn:
        cursor = conn.execute("""
            INSERT OR IGNORE INTO files (file_path, file_name, project_folder, file_size, extension, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)
        """, (file_path, path.name, project_folder, file_size, extension, now, now))
        conn.commit()
        if cursor.lastrowid:
            return cursor.lastrowid
        # Already exists — return existing id
        row = conn.execute("SELECT id FROM files WHERE file_path = ?", (file_path,)).fetchone()
        return row["id"] if row else -1


def get_file_hash(file_path: str) -> Optional[str]:
    """Compute fast hash using first+last 1MB of file."""
    path = Path(file_path)
    try:
        file_size = path.stat().st_size
        h = hashlib.md5()
        with open(path, "rb") as f:
            # First 1MB
            h.update(f.read(1024 * 1024))
            if file_size > 2 * 1024 * 1024:
                # Last 1MB
                f.seek(-1024 * 1024, 2)
                h.update(f.read(1024 * 1024))
        return h.hexdigest()
    except Exception:
        return None


def check_hash(file_path: str, new_hash: str) -> str:
    """
    Returns: 'skip' | 'reprocess' | 'new'
    """
    with get_connection() as conn:
        row = conn.execute(
            "SELECT file_hash, status FROM files WHERE file_path = ?", (file_path,)
        ).fetchone()
        if not row:
            return "new"
        if row["file_hash"] == new_hash and row["status"] == "done":
            return "skip"
        return "reprocess"


def update_status(file_path: str, status: str, file_hash: str = None,
                  chunk_count: int = None, error: str = None):
    now = time.time()
    fields = ["status = ?", "updated_at = ?"]
    values = [status, now]
    if file_hash:
        fields.append("file_hash = ?")
        values.append(file_hash)
    if chunk_count is not None:
        fields.append("chunk_count = ?")
        values.append(chunk_count)
    if error:
        fields.append("error_message = ?")
        values.append(error)
    if status == "done":
        fields.append("processed_at = ?")
        values.append(now)
    values.append(file_path)
    with get_connection() as conn:
        conn.execute(f"UPDATE files SET {', '.join(fields)} WHERE file_path = ?", values)
        conn.commit()


def reset_project_hashes(project_folder: str):
    """Clear stored hashes for a project so all files get reprocessed on next index."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE files SET file_hash = NULL, status = 'pending' WHERE project_folder = ?",
            (project_folder,)
        )
        conn.commit()


def get_project_file_paths(project_folder: str) -> list:
    """Return all file paths registered under a project."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT file_path FROM files WHERE project_folder = ?", (project_folder,)
        ).fetchall()
    return [row["file_path"] for row in rows]


def get_pending_files(project_folder: str = None) -> list:
    with get_connection() as conn:
        if project_folder:
            return conn.execute(
                "SELECT * FROM files WHERE status IN ('pending', 'in_progress') AND project_folder = ?",
                (project_folder,)
            ).fetchall()
        return conn.execute(
            "SELECT * FROM files WHERE status IN ('pending', 'in_progress')"
        ).fetchall()


def get_project_stats(project_folder: str) -> dict:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT status, COUNT(*) as count, SUM(chunk_count) as chunks
            FROM files WHERE project_folder = ?
            GROUP BY status
        """, (project_folder,)).fetchall()
        stats = {"total": 0, "done": 0, "pending": 0, "failed": 0, "total_chunks": 0}
        for row in rows:
            stats[row["status"]] = row["count"]
            stats["total"] += row["count"]
            stats["total_chunks"] += (row["chunks"] or 0)
        return stats


def log_query(project_folder: str, question: str, answer_preview: str,
              chunks_used: int, top_score: float, mean_score: float,
              min_score: float, source_files: list, latency_ms: int,
              had_safety: bool):
    """Log a completed query for analytics tracking."""
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO query_log
            (project_folder, question, answer_preview, chunks_used,
             top_relevance_score, mean_relevance_score, min_relevance_score,
             source_files, latency_ms, had_safety_flag, asked_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (project_folder, question, answer_preview, chunks_used,
              top_score, mean_score, min_score,
              json.dumps(source_files), latency_ms, int(had_safety), time.time()))
        conn.commit()


def get_query_history(project_folder: str, limit: int = 100) -> list:
    """Return recent queries for a project, newest first."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT * FROM query_log
            WHERE project_folder = ?
            ORDER BY asked_at DESC LIMIT ?
        """, (project_folder, limit)).fetchall()
    return [dict(r) for r in rows]


def get_query_metrics_summary(project_folder: str) -> dict:
    """Aggregate stats across all queries for a project."""
    with get_connection() as conn:
        row = conn.execute("""
            SELECT
                COUNT(*) as total_queries,
                AVG(mean_relevance_score) as avg_relevance,
                AVG(latency_ms) as avg_latency_ms,
                AVG(chunks_used) as avg_chunks,
                MAX(top_relevance_score) as best_score,
                SUM(had_safety_flag) as safety_count
            FROM query_log WHERE project_folder = ?
        """, (project_folder,)).fetchone()
    return dict(row) if row else {}


def get_all_projects() -> list:
    with get_connection() as conn:
        return conn.execute(
            "SELECT DISTINCT project_folder FROM files ORDER BY project_folder"
        ).fetchall()
