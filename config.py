"""
Configuration for the AZ-900 AI Tutor system.
"""
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
INDEX_DIR = BASE_DIR / "index"

FAISS_INDEX_PATH = INDEX_DIR / "az900.faiss"
CHUNKS_STORE_PATH = INDEX_DIR / "chunks.json"

# ── Chunking ───────────────────────────────────────────────────────────
MIN_CHUNK_WORDS = 200
MAX_CHUNK_WORDS = 500
CHUNK_OVERLAP_WORDS = 50  # overlap between consecutive chunks

# ── Embedding Model ────────────────────────────────────────────────────
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384  # output dim for all-MiniLM-L6-v2

# ── Retrieval ──────────────────────────────────────────────────────────
TOP_K = 3  # number of chunks to retrieve per query

# ── Generator Model ────────────────────────────────────────────────────
GENERATOR_MODEL_NAME = "google/flan-t5-base"
MAX_NEW_TOKENS = 512
