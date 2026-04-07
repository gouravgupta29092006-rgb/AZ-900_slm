"""
Embeddings & Vector Store Module
---------------------------------
Generates embeddings with sentence-transformers (all-MiniLM-L6-v2)
and stores/retrieves them via a FAISS index.
"""

import os
import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"
VECTORSTORE_DIR = os.path.join(os.path.dirname(__file__), "vectorstore")
INDEX_PATH = os.path.join(VECTORSTORE_DIR, "faiss.index")
CHUNKS_PATH = os.path.join(VECTORSTORE_DIR, "chunks.json")

# Lazy-loaded singleton
_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    """Load the sentence-transformer model (cached after first call)."""
    global _model
    if _model is None:
        print(f"  🤖 Loading embedding model: {MODEL_NAME}")
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def build_index(chunks: list[str]) -> None:
    """Generate embeddings for all chunks and save a FAISS index."""
    os.makedirs(VECTORSTORE_DIR, exist_ok=True)

    model = get_model()
    print(f"  📐 Generating embeddings for {len(chunks)} chunks...")
    embeddings = model.encode(chunks, show_progress_bar=True, convert_to_numpy=True)
    embeddings = embeddings.astype("float32")

    # Normalize for cosine similarity (use IndexFlatIP after normalization)
    faiss.normalize_L2(embeddings)

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)  # Inner Product on L2-normalized = cosine sim
    index.add(embeddings)

    faiss.write_index(index, INDEX_PATH)

    with open(CHUNKS_PATH, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

    print(f"  💾 FAISS index saved ({index.ntotal} vectors, dim={dim})")
    print(f"  💾 Chunks saved to {CHUNKS_PATH}")


def load_index() -> tuple[faiss.Index, list[str]]:
    """Load the FAISS index and chunk list from disk."""
    if not os.path.exists(INDEX_PATH):
        raise FileNotFoundError(
            f"FAISS index not found at {INDEX_PATH}. Run `python build_vectorstore.py` first."
        )
    if not os.path.exists(CHUNKS_PATH):
        raise FileNotFoundError(
            f"Chunks file not found at {CHUNKS_PATH}. Run `python build_vectorstore.py` first."
        )

    index = faiss.read_index(INDEX_PATH)

    with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    print(f"  📂 Loaded FAISS index ({index.ntotal} vectors)")
    return index, chunks


def search(query: str, top_k: int = 3) -> list[dict]:
    """
    Embed a query and retrieve the top-k most relevant chunks.

    Returns a list of dicts with 'chunk', 'score', and 'index' keys.
    """
    index, chunks = load_index()
    model = get_model()

    query_vec = model.encode([query], convert_to_numpy=True).astype("float32")
    faiss.normalize_L2(query_vec)

    scores, indices = index.search(query_vec, top_k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < len(chunks):
            results.append({
                "chunk": chunks[idx],
                "score": float(score),
                "index": int(idx),
            })

    return results
