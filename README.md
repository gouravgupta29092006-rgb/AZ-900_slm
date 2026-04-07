# AZ-900 AI Tutor — Offline RAG Backend

A fully offline, retrieval-augmented generation (RAG) system that serves as an intelligent tutor for the **Microsoft AZ-900: Azure Fundamentals** certification.

## Architecture

```
┌──────────────┐     ┌──────────────────┐     ┌────────────────┐
│   PDF Files  │────▶│  Text Extraction │────▶│  Chunking      │
│   (data/)    │     │  (PyMuPDF)       │     │  (200-500 wds) │
└──────────────┘     └──────────────────┘     └───────┬────────┘
                                                      │
                                                      ▼
┌──────────────┐     ┌──────────────────┐     ┌────────────────┐
│  FAISS Index │◀────│  Embeddings      │◀────│  Chunks        │
│  (vectorstore)│    │  (MiniLM-L6-v2)  │     │                │
└──────┬───────┘     └──────────────────┘     └────────────────┘
       │
       │  GET /ask?query=...
       ▼
┌──────────────┐     ┌──────────────────┐     ┌────────────────┐
│  Top-3 Match │────▶│  Flan-T5         │────▶│  Structured    │
│  Retrieval   │     │  (Local LLM)     │     │  JSON Response │
└──────────────┘     └──────────────────┘     └────────────────┘
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Add Your PDFs

Place your AZ-900 study material PDF files into the `data/` folder.

### 3. Build the Vector Store

```bash
python build_vectorstore.py
```

This will:
- Extract text from all PDFs in `data/`
- Clean and split into 200–500 word chunks
- Generate embeddings with `all-MiniLM-L6-v2`
- Save the FAISS index to `vectorstore/`

### 4. Start the API Server

```bash
python main.py
```

Server runs at `http://localhost:8000`.

### 5. Ask Questions

```bash
curl "http://localhost:8000/ask?query=what+is+azure"
```

Or open the interactive API docs at `http://localhost:8000/docs`.

## API Endpoints

### `GET /` — Health Check
Returns service info and status.

### `GET /ask?query=<question>&top_k=3` — Ask a Question
**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query`   | str  | required | Your AZ-900 question (3-500 chars) |
| `top_k`   | int  | 3 | Number of chunks to retrieve (1-10) |

**Response:**
```json
{
  "query": "What is Azure?",
  "definition": "...",
  "simple_explanation": "...",
  "real_world_example": "...",
  "mcq": {
    "question": "...",
    "options": [
      {"label": "A", "text": "..."},
      {"label": "B", "text": "..."},
      {"label": "C", "text": "..."},
      {"label": "D", "text": "..."}
    ],
    "correct_answer": "A"
  },
  "sources": [
    {"chunk_index": 12, "relevance_score": 0.8421},
    {"chunk_index": 5, "relevance_score": 0.7893},
    {"chunk_index": 31, "relevance_score": 0.7456}
  ],
  "response_time_seconds": 3.42
}
```

### `GET /stats` — Knowledge Base Stats
Returns statistics about the indexed content.

## Project Structure

```
az900-tutor/
├── data/                  # Place AZ-900 PDF files here
├── vectorstore/           # Auto-generated FAISS index & chunks
│   ├── faiss.index
│   └── chunks.json
├── ingest.py              # PDF loading, cleaning, chunking
├── embeddings.py          # Sentence-transformer embeddings + FAISS
├── generator.py           # Flan-T5 answer generation
├── build_vectorstore.py   # One-time index builder
├── main.py                # FastAPI application
├── requirements.txt       # Python dependencies
└── README.md              # This file
```

## Key Design Decisions

- **Fully Offline**: No OpenAI, no external APIs. All models run locally.
- **Lightweight**: Uses `all-MiniLM-L6-v2` (~80MB) and `flan-t5-base` (~950MB).
- **Cosine Similarity**: FAISS index uses L2-normalized vectors with inner product for cosine similarity search.
- **Structured Output**: Every response includes definition, explanation, example, and an MCQ — ideal for exam prep.
- **Fallback MCQ**: If the LLM output can't be parsed into a proper MCQ, a template-based question is generated.

## Constraints

- ✅ Fully offline
- ✅ No OpenAI or external APIs
- ✅ Lightweight (runs on CPU)
- ✅ Retrieval-based generation only (answers grounded in source material)
