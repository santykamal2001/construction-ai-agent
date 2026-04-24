"""
ChromaDB vector store — BGE embeddings with query-instruction prefix for best retrieval accuracy.
"""
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

_model = None
_chroma_client = None
_collection = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        from src.config import EMBEDDING_MODEL
        _model = SentenceTransformer(EMBEDDING_MODEL)
        logger.info(f"Loaded embedding model: {EMBEDDING_MODEL}")
    return _model


def _embed_documents(texts: list) -> list:
    """Embed a batch of document texts (no prefix needed for BGE docs)."""
    model = _get_model()
    vecs = model.encode(texts, normalize_embeddings=True, batch_size=32, show_progress_bar=False)
    return vecs.tolist()


def _embed_query(text: str) -> list:
    """Embed a search query with BGE instruction prefix for better retrieval."""
    model = _get_model()
    prefixed = f"Represent this sentence for searching relevant passages: {text}"
    vec = model.encode(prefixed, normalize_embeddings=True)
    return vec.tolist()


def get_collection():
    global _chroma_client, _collection
    if _collection is None:
        import chromadb
        from src.config import CHROMA_DIR, CHROMA_COLLECTION
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        # No embedding_function — we handle embeddings manually for full BGE control
        _collection = _chroma_client.get_or_create_collection(
            name=CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def upsert_chunks(chunks: List[dict], project_folder: str):
    if not chunks:
        return

    collection = get_collection()
    ids, documents, metadatas = [], [], []

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

    batch_size = 50
    for i in range(0, len(ids), batch_size):
        batch_docs = documents[i:i + batch_size]
        batch_embeddings = _embed_documents(batch_docs)
        collection.upsert(
            ids=ids[i:i + batch_size],
            embeddings=batch_embeddings,
            documents=batch_docs,
            metadatas=metadatas[i:i + batch_size],
        )


def delete_file_chunks(file_path: str):
    collection = get_collection()
    collection.delete(where={"file_path": file_path})


def search(query: str, project_folder: Optional[str] = None, n_results: int = 8) -> List[Dict[str, Any]]:
    collection = get_collection()
    total = collection.count()
    if total == 0:
        return []

    where = {"project_folder": project_folder} if project_folder else None
    query_embedding = _embed_query(query)

    try:
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, total),
            where=where,
            include=["documents", "metadatas", "distances"],
        )
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return []

    output = []
    if results and results["documents"]:
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            output.append({
                "text": doc,
                "file_path": meta.get("file_path", ""),
                "file_name": meta.get("file_name", ""),
                "project_folder": meta.get("project_folder", ""),
                "chunk_index": meta.get("chunk_index", 0),
                "relevance_score": round(1 - dist, 3),
            })

    return output


def get_collection_count(project_folder: Optional[str] = None) -> int:
    return get_collection().count()
