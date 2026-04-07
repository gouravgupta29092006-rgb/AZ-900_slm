"""
Build Vector Store
------------------
Standalone script to ingest PDFs and build the FAISS index.
Run this ONCE before starting the API server.

Usage:
    python build_vectorstore.py
"""

from ingest import ingest_pipeline
from embeddings import build_index


def main():
    print("=" * 60)
    print("  AZ-900 AI Tutor — Vector Store Builder")
    print("=" * 60)
    print()

    # Step 1: Ingest PDFs
    chunks = ingest_pipeline()

    if not chunks:
        print("❌ No chunks generated. Check your PDF files in data/")
        return

    # Step 2: Build FAISS index
    print()
    print("🔄 Building FAISS vector index...")
    build_index(chunks)

    print()
    print("=" * 60)
    print("  ✅ Vector store built successfully!")
    print(f"  📊 Total chunks indexed: {len(chunks)}")
    print("  🚀 You can now start the API: python main.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
