# DEST AI Inspector

> AI-powered document intelligence platform for construction project management.  
> Ask natural language questions across inspection reports, proposals, blueprints, and field documents — get cited, source-traceable answers in seconds.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35%2B-FF4B4B?logo=streamlit&logoColor=white)
![Claude](https://img.shields.io/badge/Claude-Opus%204-8B5CF6?logo=anthropic&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector%20DB-orange)
![License](https://img.shields.io/badge/License-MIT-green)

---

## What It Does

Construction projects generate thousands of documents — inspection reports, safety audits, proposals, contracts, blueprints, RFIs, and field notes. Finding specific information manually takes hours.

**DEST AI Inspector** indexes all of it and lets your team ask questions in plain English:

- *"What safety violations were flagged in the bridge inspection last month?"*
- *"Find all proposals we won from client Tylin between 2020 and 2025"*
- *"Which projects have outstanding structural concerns?"*
- *"Summarize the foundation inspection findings for Project C"*

The system returns precise answers with **document citations** — so you always know exactly which file, page, and section the answer came from.

---

## Key Features

| Feature | Description |
|---|---|
| **Multi-format ingestion** | PDF, DOCX, XLSX, CSV, PPTX, TXT, MD, RTF |
| **OCR for scanned PDFs** | PaddleOCR automatically handles image-based documents |
| **Semantic search** | Sentence-transformers embeddings + ChromaDB vector store |
| **AI Q&A with citations** | Claude Opus 4 answers with source file + chunk references |
| **Multi-turn chat** | Full conversation history within each session |
| **Analytics dashboard** | Query trends, document stats, processing metrics |
| **Deduplication** | MD5 hash-based — unchanged files are never re-processed |
| **Project isolation** | Each project folder is independently searchable |
| **Safety flagging** | Automatic detection of safety-related keywords in answers |

---

## Tech Stack

```
Frontend          Streamlit (custom CSS — Stripe/Notion-inspired light theme)
AI Model          Anthropic Claude Opus 4 (via API)
Embeddings        sentence-transformers / all-MiniLM-L6-v2 (local, no API needed)
Vector Database   ChromaDB (on-disk, no server required)
Metadata Store    SQLite
PDF Extraction    PyMuPDF (text) + PaddleOCR (scanned/image pages)
Office Docs       python-docx, openpyxl, python-pptx
Visualization     Plotly
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Streamlit UI                         │
│   Dashboard │ Ask AI │ Documents │ Projects │ Analytics │
└──────────────────────┬──────────────────────────────────┘
                       │
         ┌─────────────▼─────────────┐
         │      RAG Pipeline         │
         │  Query → Embed → Search   │
         │  → Context → Claude API   │
         └─────────────┬─────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
   ChromaDB        SQLite         Claude API
  (vectors)      (metadata)      (answers)

Ingestion Pipeline:
  Folder Scan → Hash Check → Text Extract → Chunk (800c/150 overlap)
              → Embed (local) → ChromaDB → SQLite log
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

# Run setup (creates venv + installs dependencies)
chmod +x setup.sh && ./setup.sh
```

### Configure API Key

```bash
cp .env.example .env
# Edit .env and add your Anthropic API key
```

### Run

```bash
./run.sh
# Opens at http://localhost:8501
```

---

## Usage

### 1. Index a Project

1. Open the **Projects** tab in the sidebar
2. Enter the path to your project folder (containing PDFs, DOCX, etc.)
3. Click **Process Project** — the pipeline extracts, chunks, and indexes all documents
4. Status updates in real-time; large folders with scanned PDFs may take a few minutes

### 2. Ask Questions

1. Open the **Ask AI** tab
2. Select the project to search (or "All Projects" for cross-project queries)
3. Type your question in natural language
4. The answer includes:
   - AI-generated response from Claude
   - Source citations (file name + chunk)
   - Confidence score
   - Safety flag if relevant

### 3. Browse Documents

The **Documents** tab shows all indexed files with status, chunk count, and file type.

---

## Project Structure

```
construction-ai-agent/
├── app.py                  # Streamlit application (UI + routing)
├── src/
│   ├── agent.py            # Claude API integration + RAG query engine
│   ├── vector_store.py     # ChromaDB read/write operations
│   ├── processor.py        # Main ingestion pipeline orchestrator
│   ├── extractor.py        # Multi-format text extraction + OCR
│   ├── chunker.py          # Text splitting with overlap
│   ├── database.py         # SQLite schema + queries
│   └── config.py           # Configuration constants
├── sample_data/            # Example construction documents
│   ├── ProjectA_Bridge_Inspection/
│   ├── ProjectB_Highway_Repair/
│   └── ProjectC_Building_Foundation/
├── .env.example            # Environment variable template
├── requirements.txt        # Python dependencies
├── setup.sh                # One-command environment setup
└── run.sh                  # Start the application
```

---

## Configuration

All tunable parameters are in [src/config.py](src/config.py):

| Parameter | Default | Description |
|---|---|---|
| `CHUNK_SIZE` | 800 chars | Text chunk size (~200 tokens) |
| `CHUNK_OVERLAP` | 150 chars | Overlap between consecutive chunks |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Local sentence-transformer model |
| `CLAUDE_MODEL` | `claude-opus-4-6` | Anthropic model for Q&A |
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

## Security Notes

- Your documents never leave your machine — embeddings are generated locally
- Only the final query + retrieved text chunks are sent to the Claude API
- API key is stored in `.env` (never committed to git)
- The `.gitignore` excludes all data directories and database files

---

## Contributing

Pull requests are welcome. For major changes, please open an issue first.

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

*Built for construction teams who need answers, not more folders to search.*
