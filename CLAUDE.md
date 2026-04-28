# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Servers

**FastAPI (primary — serves the React UI):**
```bash
source venv/bin/activate
uvicorn api:app --reload --port 8000
# Verify: curl http://localhost:8000/health
```

**Streamlit (legacy UI — optional):**
```bash
./run.sh   # http://localhost:8501
```

**First-time setup:**
```bash
chmod +x setup.sh && ./setup.sh
cp .env.example .env   # then add ANTHROPIC_API_KEY
```

There are no tests and no linter configured. The venv is at `./venv/`.

## Architecture

Two servers, two databases, one RAG pipeline:

```
React UI (port 3001)
    └── FastAPI api.py (port 8000)
            ├── src/processor.py  → scan + index documents
            ├── src/agent.py      → RAG query + Claude call
            ├── src/vector_store.py → ChromaDB (vectors)
            └── src/database.py   → SQLite (metadata + query log)
```

**Ingestion flow** (`processor.process_project`):
1. Walk folder → register files in SQLite
2. Per file: compute MD5 hash → skip if unchanged (`check_hash` returns `"skip"`)
3. Extract text (`extractor.py` — PyMuPDF first, PaddleOCR fallback for scanned pages)
4. Chunk (`chunker.py` — 1200 chars / 200 overlap)
5. Embed (`vector_store._embed_documents` — no prefix for docs) → upsert into ChromaDB

**Query flow** (`agent.query`):
1. Embed query with BGE instruction prefix (`"Represent this sentence for searching relevant passages: "`) — this asymmetry is intentional and critical for BGE accuracy
2. Retrieve `max(n_results * 3, 24)` candidates from ChromaDB
3. Deduplicate: max 6 chunks per file + Jaccard similarity check (>0.85 = skip)
4. Cross-encoder rerank (`ms-marco-MiniLM-L-6-v2`) → keep top `n_results`
5. Build context string → Claude Opus 4 with system prompt → return answer + sources

## Key Invariants

**ChromaDB collection name:** `dest_docs_v2` (defined in `config.py`). The old collection `dest_docs` used `all-MiniLM-L6-v2` (384-dim) — never change the name back or mix models into the same collection; embedding dimensions are incompatible.

**Embedding model:** `BAAI/bge-base-en-v1.5` (768-dim). Documents are embedded without a prefix; queries must use the instruction prefix. This is the BGE asymmetric retrieval contract — changing one without the other silently degrades quality.

**API key location:** `ANTHROPIC_API_KEY` is loaded from `.env` via `python-dotenv` in `api.py` and `app.py`. It is never passed to the React frontend. The `/health` endpoint returns `api_connected: true/false` but not the key itself.

**Project isolation:** Each project folder in `sample_data/` is a separate ChromaDB namespace (`project_folder` metadata field). All queries and stats are scoped by this name — it equals the folder's `.name`, not its full path.

**File deduplication:** `database.get_file_hash` uses first+last 1MB MD5 (not full file) for speed on large PDFs. Only `status == "done"` + matching hash triggers a skip.

**Reranker lazy loading:** Both `_model` (embedding) and `_reranker` (cross-encoder) are module-level singletons loaded on first use. `_reranker = False` (not `None`) signals a failed load so the condition `if _reranker` correctly skips retrying.

## Data Layout

```
data/
├── chroma_db/     # ChromaDB persistent storage (git-ignored)
└── metadata.db    # SQLite: files table + query_log table (git-ignored)

sample_data/       # Source documents — one subfolder per project
```

## Config Reference (`src/config.py`)

| Constant | Value | Notes |
|---|---|---|
| `CHUNK_SIZE` | 1200 | chars |
| `CHUNK_OVERLAP` | 200 | chars |
| `EMBEDDING_MODEL` | `BAAI/bge-base-en-v1.5` | local, 768-dim |
| `CHROMA_COLLECTION` | `dest_docs_v2` | do not rename |
| `RERANKER_MODEL` | `cross-encoder/ms-marco-MiniLM-L-6-v2` | local |
| `CLAUDE_MODEL` | `claude-opus-4-6` | |
| `MAX_WORKERS` | 4 | parallel file workers |

## FastAPI Endpoints

| Endpoint | Notes |
|---|---|
| `GET /health` | Returns `api_connected` bool — no key exposed |
| `GET /projects` | Reads `sample_data/` subdirs + SQLite stats |
| `POST /index/{project_name}` | Runs full `process_project`; `force=true` deletes existing vectors first |
| `POST /query` | Runs RAG pipeline, logs result to `query_log` |
| `GET /documents/{project_name}` | SQLite `files` table for the project |
| `GET /stats/{project_name}` | Aggregate counts from `files` table |
| `GET /analytics/{project_name}` | Summary metrics + query history + type distribution |

## System Prompt Notes

`agent.SYSTEM_PROMPT` contains domain-specific instructions for construction inspection documents. Key rules baked in:
- Field values often appear on the line **after** their label in scanned forms — the prompt instructs Claude to read them together.
- **Document Reviewers** (approval stamp signers) must not be listed as project workers — only `DESI Insp:` and `Contractor Rep:` field values count as personnel.

Modifying the system prompt affects answer quality for all queries; test against the sample data projects before changing it.
