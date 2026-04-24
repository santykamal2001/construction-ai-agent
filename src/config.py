import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
CHROMA_DIR = DATA_DIR / "chroma_db"
SQLITE_PATH = DATA_DIR / "metadata.db"

# Chunking
CHUNK_SIZE = 800        # characters (~200 tokens)
CHUNK_OVERLAP = 150     # characters overlap between chunks

# Embedding
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # fast local model

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
