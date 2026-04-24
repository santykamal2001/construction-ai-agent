# DEST AI Inspector — Backend

> AI-powered RAG backend for construction document intelligence.  
> FastAPI + ChromaDB + Claude Opus 4 — enterprise-grade retrieval with cross-encoder reranking.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688?logo=fastapi&logoColor=white)
![Claude](https://img.shields.io/badge/Claude-Opus%204-8B5CF6?logo=anthropic&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector%20DB-orange)
![License](https://img.shields.io/badge/License-MIT-green)

---

## What It Does

Construction projects generate thousands of documents — inspection reports, safety audits, proposals, contracts, blueprints, RFIs, and field notes. Finding specific information manually takes hours.

**DEST AI Inspector backend** indexes everything and answers natural-language questions with source citations:

- *"What safety violations were flagged in the bridge inspection last month?"*
- *"Find all proposals we won from client Tylin between 2020 and 2025"*
- *"Which projects have outstanding structural concerns?"*
- *"Summarize the foundation inspection findings for Project C"*

Answers come back with **document citations, relevance scores, and latency metrics** — suitable for enterprise deployment.

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│               React UI (dest-ai-inspector)               │
│    Ask AI │ Analytics │ Documents │ System               │
└──────────────────────┬───────────────────────────────────┘
                       │ HTTP / JSON
         ┌─────────────▼──────────────┐
         │       FastAPI (port 8000)  │
         │  /health  /query  /index   │
         │  /projects  /documents     │
         │  /stats     /analytics     │
         └──────┬───────────┬─────────┘
                │           │
     ┌──────────▼──┐   ┌────▼────────┐
     │  RAG Pipeline│   │ SQLite DB   │
     │  BGE Embed   │   │ (metadata)  │
     │  ChromaDB    │   └─────────────┘
     │  Reranker    │
     └──────┬───────┘
            │
     ┌──────▼───────┐
     │  Claude API  │
     │  (answers)   │
     └──────────────┘

Ingestion Pipeline:
  Folder Scan → Hash Check → Text Extract → Chunk (1200c / 200 overlap)
              → BGE Embed (local) → ChromaDB → SQLite log
```

---

## Performance Stack

| Layer | Choice | Why |
|---|---|---|
| Embeddings | `BAAI/bge-base-en-v1.5` (768-dim) | ~8 pts better on MTEB vs MiniLM; asymmetric retrieval with instruction prefix |
| Vector DB | ChromaDB `dest_docs_v2` | On-disk, no server; separate collection avoids mixing old MiniLM vectors |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Re-scores 24 candidates → returns top 8; major precision lift |
| LLM | Claude Opus 4 | Best-in-class reasoning for construction domain |
| Chunk size | 1200 chars / 200 overlap | Better context window utilisation vs old 800/150 |

**Query flow:** embed query with BGE instruction prefix → retrieve 24 candidates → deduplicate → cross-encoder rerank → top 8 → Claude synthesis

---

## Key Features

| Feature | Description |
|---|---|
| **Multi-format ingestion** | PDF, DOCX, XLSX, CSV, PPTX, TXT, MD, RTF |
| **OCR for scanned PDFs** | PaddleOCR automatically handles image-based documents |
| **BGE semantic search** | `bge-base-en-v1.5` with query instruction prefix for asymmetric retrieval |
| **Cross-encoder reranking** | `ms-marco-MiniLM-L-6-v2` re-scores candidates before sending to LLM |
| **AI Q&A with citations** | Claude Opus 4 answers with source file + chunk references |
| **FastAPI REST server** | JSON API consumed by React UI — CORS-enabled for port 3001 |
| **Analytics endpoint** | Query history, latency, relevance trends, file type distribution |
| **Deduplication** | MD5 hash — unchanged files are never re-processed |
| **Project isolation** | Each project folder is independently searchable |
| **Safety flagging** | Automatic detection of safety-related keywords in answers |
| **Secure API key** | Stored in `.env` only — never exposed to frontend or UI |

---

## Tech Stack

```
API Server        FastAPI + Uvicorn (port 8000)
AI Model          Anthropic Claude Opus 4 (via API)
Embeddings        BAAI/bge-base-en-v1.5 (local, 768-dim, no API needed)
Reranker          cross-encoder/ms-marco-MiniLM-L-6-v2 (local)
Vector Database   ChromaDB (on-disk, collection: dest_docs_v2)
Metadata Store    SQLite
PDF Extraction    PyMuPDF (text) + PaddleOCR (scanned/image pages)
Office Docs       python-docx, openpyxl, python-pptx
Legacy UI         Streamlit (app.py — functional on port 8501)
```

---

## Quick Start

### Prerequisites
- Python 3.10+
- Anthropic API key → [console.anthropic.com](https://console.anthropic.com)

### Installation

```bash
git clone https://github.com/YOUR_USERNAME/construction-ai-agent.git
cd construction-ai-agent

# Create venv and install all dependencies
chmod +x setup.sh && ./setup.sh
```

### Configure API Key

```bash
cp .env.example .env
# Edit .env and set your key:
# ANTHROPIC_API_KEY=sk-ant-...
```

The key is loaded server-side only. It is never sent to or stored in the React frontend.

### Start the FastAPI Server

```bash
source venv/bin/activate
uvicorn api:app --reload --port 8000
```

Verify it's running:
```bash
curl http://localhost:8000/health
# {"status":"ok","api_connected":true}
```

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Backend status + Anthropic API key validation |
| `GET` | `/projects` | List all indexed project folders with stats |
| `POST` | `/index/{project}` | Trigger full index / reindex of a project |
| `POST` | `/query` | RAG query with reranking → Claude answer |
| `GET` | `/documents/{project}` | All indexed files with status and chunk count |
| `GET` | `/stats/{project}` | File counts and chunk totals |
| `GET` | `/analytics/{project}` | Query history, latency, type distribution |

### Query Request

```json
{
  "question": "What safety issues were found?",
  "project": "ProjectA_Bridge_Inspection",
  "n_results": 8
}
```

### Query Response

```json
{
  "answer": "The inspection found...",
  "sources": [{ "file_name": "report.pdf", "relevance_score": 0.91, "excerpt": "..." }],
  "chunks_used": 8,
  "latency_ms": 1240,
  "mean_relevance_score": 0.87,
  "safety": false
}
```

---

## Project Structure

```
construction-ai-agent/
├── api.py                  # FastAPI server — REST API for React UI
├── app.py                  # Streamlit UI (legacy — still functional)
├── src/
│   ├── agent.py            # Claude RAG engine + cross-encoder reranking
│   ├── vector_store.py     # ChromaDB + BGE embeddings (manual, with prefix)
│   ├── processor.py        # Ingestion pipeline orchestrator
│   ├── extractor.py        # Multi-format text extraction + OCR
│   ├── chunker.py          # Text splitting with overlap
│   ├── database.py         # SQLite schema + queries
│   └── config.py           # Configuration constants
├── sample_data/            # Example construction documents
├── .env.example            # Template — no real keys
├── .env                    # Your API key — git-ignored
├── requirements.txt        # Python dependencies
├── setup.sh                # One-command environment setup
└── run.sh                  # Start Streamlit (legacy)
```

---

## Configuration

All tunable parameters are in [src/config.py](src/config.py):

| Parameter | Value | Description |
|---|---|---|
| `CHUNK_SIZE` | 1200 chars | Larger chunks for better context coverage |
| `CHUNK_OVERLAP` | 200 chars | Overlap between consecutive chunks |
| `EMBEDDING_MODEL` | `BAAI/bge-base-en-v1.5` | 768-dim, top MTEB benchmark performer |
| `CHROMA_COLLECTION` | `dest_docs_v2` | Separate from legacy MiniLM collection |
| `RERANKER_MODEL` | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Precision reranking model |
| `CLAUDE_MODEL` | `claude-opus-4-6` | Anthropic model used for Q&A generation |
| `MAX_WORKERS` | 4 | Parallel file processing workers |

---

## Supported File Types

| Format | Library | Notes |
|---|---|---|
| PDF (text) | PyMuPDF | Fast, preserves page numbers |
| PDF (scanned) | PaddleOCR | Auto-detected, OCR on image pages |
| DOCX / DOC | python-docx | Paragraphs + tables |
| XLSX / XLS | openpyxl | All sheets |
| CSV | Built-in | UTF-8 + Latin-1 fallback |
| PPTX / PPT | python-pptx | Per-slide text |
| TXT / MD / RTF | Built-in | Multi-encoding support |

---

## Security

- Documents never leave your machine — embeddings are generated locally
- Only the query + retrieved text chunks are sent to the Claude API
- API key is in `.env` only — never committed, never sent to any frontend
- `.gitignore` excludes `.env`, all data directories, and ChromaDB files
- CORS is restricted to `http://localhost:3001` (React dev server)

---

## Pair With the React UI

The companion React frontend lives in [`dest-ai-inspector`](../dest-ai-inspector).  
Start this FastAPI server first, then run `npm run dev` in the React project.

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

*Built for construction teams who need answers, not more folders to search.*
