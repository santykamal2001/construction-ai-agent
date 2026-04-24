import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
CHROMA_DIR = DATA_DIR / "chroma_db"
SQLITE_PATH = DATA_DIR / "metadata.db"

# Chunking
CHUNK_SIZE = 1200       # larger chunks = more context per retrieval
CHUNK_OVERLAP = 200     # wider overlap preserves cross-boundary context

# Embedding — BGE-base outperforms MiniLM on MTEB by ~8 points
EMBEDDING_MODEL = "BAAI/bge-base-en-v1.5"
CHROMA_COLLECTION = "dest_docs_v2"   # new name avoids stale MiniLM vectors

# Cross-encoder reranker — re-scores top-k candidates after ANN retrieval
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

# Claude API
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-opus-4-6"

# Processing
BATCH_SIZE = 50         # chunks per DB write
MAX_WORKERS = 4         # parallel file workers

# Supported file extensions
SUPPORTED_EXTENSIONS = {
    ".txt", ".md", ".pdf", ".docx", ".doc",
    ".xlsx", ".xls", ".csv", ".pptx", ".ppt",
    ".rtf", ".odt"
}

# Priority buckets by file size
SIZE_SMALL = 10 * 1024 * 1024       # < 10MB → fast queue
SIZE_MEDIUM = 500 * 1024 * 1024     # 10MB–500MB → normal queue
SIZE_LARGE = 5 * 1024 * 1024 * 1024 # > 5GB → split first
