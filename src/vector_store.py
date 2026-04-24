"""
ChromaDB vector store wrapper.
Handles embedding generation and similarity search.
"""
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

_embedding_fn = None
_chroma_client = None
_collection = None


def _get_embedding_function():
    global _embedding_fn
    if _embedding_fn is None:
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
        from src.config import EMBEDDING_MODEL
        _embedding_fn = SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)
    return _embedding_fn


def get_collection():
    global _chroma_client, _collection
    if _collection is None:
        import chromadb
        from src.config import CHROMA_DIR
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        _collection = _chroma_client.get_or_create_collection(
            name="construction_docs",
            embedding_function=_get_embedding_function(),
            metadata={"hnsw:space": "cosine"}
        )
    return _collection


def upsert_chunks(chunks: List[dict], project_folder: str):
    """
    Store chunks in ChromaDB.
    Each chunk: {text, chunk_index, file_path, ...}
    """
    if not chunks:
        return

    collection = get_collection()
    ids = []
    documents = []
    metadatas = []

    for chunk in chunks:
        chunk_id = f"{chunk['file_path']}::chunk_{chunk['chunk_index']}"
        ids.append(chunk_id)
        documents.append(chunk["text"])
        metadatas.append({
            "file_path": chunk["file_path"],
            "chunk_index": chunk["chunk_index"],
            "project_folder": project_folder,
            "file_name": chunk["file_path"].split("/")[-1],
        })

    # Upsert in batches of 50
    batch_size = 50
    for i in range(0, len(ids), batch_size):
        collection.upsert(
            ids=ids[i:i+batch_size],
            documents=documents[i:i+batch_size],
            metadatas=metadatas[i:i+batch_size],
        )


def delete_file_chunks(file_path: str):
    """Remove all chunks for a file (used when file is deleted/reprocessed)."""
    collection = get_collection()
    collection.delete(where={"file_path": file_path})


def search(query: str, project_folder: Optional[str] = None, n_results: int = 8) -> List[Dict[str, Any]]:
    """
    Semantic search. Returns list of results with text, metadata, distance.
    """
    collection = get_collection()

    where = None
    if project_folder:
        where = {"project_folder": project_folder}

    try:
        results = collection.query(
            query_texts=[query],
            n_results=min(n_results, collection.count() or 1),
            where=where,
            include=["documents", "metadatas", "distances"]
        )
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return []

    output = []
    if results and results["documents"]:
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        ):
            output.append({
                "text": doc,
                "file_path": meta.get("file_path", ""),
                "file_name": meta.get("file_name", ""),
                "project_folder": meta.get("project_folder", ""),
                "chunk_index": meta.get("chunk_index", 0),
                "relevance_score": round(1 - dist, 3),  # cosine: 1=identical
            })

    return output


def get_collection_count(project_folder: Optional[str] = None) -> int:
    collection = get_collection()
    if project_folder:
        return collection.count()  # ChromaDB doesn't support filtered count easily
    return collection.count()
