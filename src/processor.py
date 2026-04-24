"""
Main processing pipeline:
  Scan folder → Register files → Extract text → Chunk → Embed → Store

For demo: runs synchronously (no Redis/RabbitMQ needed).
Production: each step would feed a job queue.
"""
import logging
import os
from pathlib import Path
from typing import Callable, Optional

from src import database, vector_store
from src.chunker import chunk_text
from src.config import SUPPORTED_EXTENSIONS
from src.extractor import extract_text

logger = logging.getLogger(__name__)


def scan_folder(folder_path: str, progress_callback: Optional[Callable] = None) -> int:
    """
    Phase 1: Walk folder tree and register all supported files in DB.
    Returns count of newly registered files.
    """
    database.init_db()
    folder = Path(folder_path)
    project_name = folder.name
    registered = 0

    all_files = [
        f for f in folder.rglob("*")
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    ]

    for i, file_path in enumerate(all_files):
        try:
            file_size = file_path.stat().st_size
            ext = file_path.suffix.lower()
            database.register_file(str(file_path), project_name, file_size, ext)
            registered += 1
            if progress_callback:
                progress_callback(i + 1, len(all_files), file_path.name)
        except Exception as e:
            logger.error(f"Failed to register {file_path}: {e}")

    return registered


def process_project(folder_path: str, progress_callback: Optional[Callable] = None) -> dict:
    """
    Full pipeline for a project folder:
    1. Scan files
    2. For each file: hash check → extract → chunk → embed → store
    Returns summary stats.
    """
    database.init_db()
    folder = Path(folder_path)
    project_name = folder.name

    # Phase 1: Scan
    total_registered = scan_folder(folder_path)

    stats = {"processed": 0, "skipped": 0, "failed": 0, "total_chunks": 0}

    all_files = [
        f for f in folder.rglob("*")
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    ]

    for i, file_path in enumerate(all_files):
        file_str = str(file_path)

        if progress_callback:
            progress_callback(i + 1, len(all_files), file_path.name, "processing")

        # Phase 3: Deduplication — hash check
        file_hash = database.get_file_hash(file_str)
        if file_hash:
            decision = database.check_hash(file_str, file_hash)
            if decision == "skip":
                stats["skipped"] += 1
                logger.info(f"SKIP (unchanged): {file_path.name}")
                continue
            elif decision == "reprocess":
                vector_store.delete_file_chunks(file_str)
                logger.info(f"RE-PROCESS (changed): {file_path.name}")

        # Mark in-progress
        database.update_status(file_str, "in_progress", file_hash=file_hash)

        try:
            # Phase 2: Extract text
            text = extract_text(file_str)
            if not text or not text.strip():
                database.update_status(file_str, "done", chunk_count=0)
                stats["skipped"] += 1
                logger.warning(f"No text extracted: {file_path.name}")
                continue

            # Phase 2: Chunk
            chunks = chunk_text(text, file_str)
            if not chunks:
                database.update_status(file_str, "done", chunk_count=0)
                continue

            # Phase 2: Embed + Store in vector DB
            vector_store.upsert_chunks(chunks, project_name)

            # Update DB
            database.update_status(file_str, "done", chunk_count=len(chunks))
            stats["processed"] += 1
            stats["total_chunks"] += len(chunks)
            logger.info(f"DONE: {file_path.name} → {len(chunks)} chunks")

        except Exception as e:
            database.update_status(file_str, "failed", error=str(e))
            stats["failed"] += 1
            logger.error(f"FAILED: {file_path.name}: {e}")

    return stats


def get_available_projects(base_folder: str) -> list:
    """List all subdirectories in base folder (each = a project)."""
    base = Path(base_folder)
    if not base.exists():
        return []
    return [d for d in sorted(base.iterdir()) if d.is_dir()]
