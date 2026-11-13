"""Shared, beginner-friendly RAG functions. Read this file after steps 1–4."""
from pathlib import Path

import chromadb
import tiktoken
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

PROJECT_DIR = Path(__file__).resolve().parent
DOCUMENT_PATH = PROJECT_DIR / "Documents" / "BrightPath_Employee_Guide.txt"
DB_PATH = PROJECT_DIR / "chroma_db"
COLLECTION_NAME = "brightpath_guide"

# This tokenizer is used to VISUALIZE tokens and split the document.
# The local embedding model has its own internal tokenizer.
TOKENIZER = tiktoken.get_encoding("cl100k_base")


def read_document():
    """Load the text document from this project's Documents folder."""
    return DOCUMENT_PATH.read_text(encoding="utf-8")


def make_chunks(text, chunk_size=180, overlap=35):
    """Split by token count, keeping an overlap between neighboring chunks."""
    if not (0 <= overlap < chunk_size):
        raise ValueError("overlap must be >= 0 and smaller than chunk_size")

    token_ids = TOKENIZER.encode(text)
    chunks = []
    start = 0
    while start < len(token_ids):
        end = min(start + chunk_size, len(token_ids))
        chunk = TOKENIZER.decode(token_ids[start:end]).strip()
        if chunk:
            chunks.append(chunk)
        if end == len(token_ids):
            break
        start = end - overlap
    return chunks


def embed_texts(texts):
    """Convert text to numeric vectors with Chroma's local embedding model."""
    model = DefaultEmbeddingFunction()  # all-MiniLM-L6-v2, local, 384 dimensions
    vectors = model(texts)
    return [v.tolist() if hasattr(v, "tolist") else list(v) for v in vectors]


def get_database():
    """Chroma's database files live inside ./chroma_db in this project."""
    return chromadb.PersistentClient(path=str(DB_PATH))


def search_chunks(question, top_k=3):
    """Embed the question, find nearby vectors, and return their source text."""
    db = get_database()
    try:
        collection = db.get_collection(COLLECTION_NAME, embedding_function=None)
    except Exception as exc:
        raise RuntimeError("No indexed collection. Run 05_store_in_chroma.py first.") from exc

    count = collection.count()
    if count == 0:
        raise RuntimeError("The collection is empty. Run 05_store_in_chroma.py first.")

    question_vector = embed_texts([question])[0]
    results = collection.query(
        query_embeddings=[question_vector],
        n_results=min(top_k, count),
        include=["documents", "metadatas", "distances"],
    )
    matches = []
    for chunk_id, text, metadata, distance in zip(
        results["ids"][0],
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        matches.append({
            "id": chunk_id,
            "text": text,
            "source": metadata.get("source", "unknown"),
            "distance": distance,
        })
    return matches
