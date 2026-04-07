"""
PDF Ingestion Module (Optimized for AZ-900 SLM)

Features:
- Multi-PDF ingestion
- Cleaning + artifact removal
- Topic tagging (improves retrieval)
- Structure hints (Definition, Example)
- Smart chunking (200–500 words)
"""

import os
import re
import fitz  # PyMuPDF

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


# ---------------------------
# PDF LOADING
# ---------------------------
def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from a single PDF."""
    doc = fitz.open(pdf_path)
    pages = []

    for page in doc:
        text = page.get_text("text")
        if text and text.strip():
            pages.append(text)

    doc.close()
    return "\n".join(pages)


def load_all_pdfs(data_dir: str = DATA_DIR) -> str:
    """Load all PDFs from data folder."""
    if not os.path.isdir(data_dir):
        raise FileNotFoundError(f"Data directory not found: {data_dir}")

    pdf_files = sorted(
        f for f in os.listdir(data_dir) if f.lower().endswith(".pdf")
    )

    if not pdf_files:
        raise FileNotFoundError(f"No PDF files found in {data_dir}")

    all_text = []

    print("📂 Loading PDFs...")
    for fname in pdf_files:
        path = os.path.join(data_dir, fname)
        print(f"  📄 {fname}")
        text = extract_text_from_pdf(path)
        all_text.append(text)

    merged = "\n\n".join(all_text)
    print(f"  ✅ Loaded {len(pdf_files)} PDF(s), {len(merged):,} characters")
    return merged


# ---------------------------
# CLEANING + STRUCTURE
# ---------------------------
def clean_text(text: str) -> str:
    """Clean text and preserve useful structure."""

    text = re.sub(r"\x0c", "", text)  # remove form feed
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)

    # Remove page numbers (standalone)
    text = re.sub(r"(?m)^\s*\d{1,4}\s*$", "", text)

    # Add structure hints
    text = re.sub(r"\bDefinition\b[:\-]?", "\n[Definition]\n", text, flags=re.IGNORECASE)
    text = re.sub(r"\bExample\b[:\-]?", "\n[Example]\n", text, flags=re.IGNORECASE)

    return text.strip()


# ---------------------------
# TOPIC TAGGING (KEY FEATURE)
# ---------------------------
def detect_topic(block: str) -> str:
    """Assign topic label to improve retrieval."""
    b = block.lower()

    if "sla" in b or "uptime" in b:
        return "SLA"
    elif "iaas" in b or "paas" in b or "saas" in b:
        return "Service Models"
    elif "security" in b or "mfa" in b or "identity" in b:
        return "Security"
    elif "storage" in b or "blob" in b or "disk" in b:
        return "Storage"
    elif "network" in b or "vnet" in b or "dns" in b:
        return "Networking"
    elif "vm" in b or "compute" in b:
        return "Compute"
    elif "pricing" in b or "cost" in b:
        return "Pricing"
    else:
        return "General"


def add_topic_markers(text: str) -> str:
    """Add topic labels to each paragraph block."""
    blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
    tagged = []

    for block in blocks:
        topic = detect_topic(block)
        tagged.append(f"[{topic}]\n{block}")

    return "\n\n".join(tagged)


# ---------------------------
# CHUNKING (CRITICAL)
# ---------------------------
def split_into_chunks(text: str, min_words=200, max_words=500):
    """
    Paragraph-aware chunking.
    Keeps chunks meaningful for retrieval.
    """

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    chunks = []
    current = []
    word_count = 0

    for para in paragraphs:
        words = para.split()
        para_len = len(words)

        # Large paragraph → split directly
        if para_len > max_words:
            if current:
                chunks.append("\n\n".join(current))
                current = []
                word_count = 0

            for i in range(0, para_len, max_words):
                chunk = " ".join(words[i:i + max_words])
                chunks.append(chunk)
            continue

        # If exceeding limit → flush chunk
        if word_count + para_len > max_words and word_count >= min_words:
            chunks.append("\n\n".join(current))
            current = []
            word_count = 0

        current.append(para)
        word_count += para_len

    # Final chunk
    if current:
        if word_count >= min_words or not chunks:
            chunks.append("\n\n".join(current))
        else:
            chunks[-1] += "\n\n" + "\n\n".join(current)

    return chunks


# ---------------------------
# MAIN PIPELINE
# ---------------------------
def ingest_pipeline(data_dir: str = DATA_DIR):
    """Full pipeline: load → clean → tag → chunk"""

    print("\n🔄 Starting ingestion pipeline...\n")

    raw_text = load_all_pdfs(data_dir)

    cleaned = clean_text(raw_text)

    tagged = add_topic_markers(cleaned)

    chunks = split_into_chunks(tagged)

    print(f"\n🧩 Created {len(chunks)} chunks")
    print("✅ Ingestion complete\n")

    return chunks


# ---------------------------
# TEST RUN
# ---------------------------
if __name__ == "__main__":
    chunks = ingest_pipeline()

    for i, chunk in enumerate(chunks[:3]):
        print(f"\n--- Chunk {i+1} ({len(chunk.split())} words) ---")
        print(chunk[:300] + "...")