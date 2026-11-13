"""STEP 5 — Embed each chunk, save its vector and text into local ChromaDB."""
from rag_core import (
    COLLECTION_NAME, DB_PATH, DOCUMENT_PATH, PROJECT_DIR,
    embed_texts, get_database, make_chunks, read_document,
)

chunks = make_chunks(read_document(), chunk_size=180, overlap=35)
print(f"1. Created {len(chunks)} text chunks.")

vectors = embed_texts(chunks)
print(f"2. Created {len(vectors)} embeddings; each has {len(vectors[0])} values.")

client = get_database()
# Re-create the collection so re-running the script removes stale old chunks.
if COLLECTION_NAME in [collection.name for collection in client.list_collections()]:
    client.delete_collection(COLLECTION_NAME)

collection = client.create_collection(
    name=COLLECTION_NAME,
    embedding_function=None,
    configuration={"hnsw": {"space": "cosine"}},
)

ids = [f"chunk_{i:03d}" for i in range(1, len(chunks) + 1)]
source = str(DOCUMENT_PATH.relative_to(PROJECT_DIR))
collection.add(
    ids=ids,
    documents=chunks,
    embeddings=vectors,
    metadatas=[{"source": source, "chunk_number": i}
               for i in range(1, len(chunks) + 1)],
)

print(f"3. Stored {collection.count()} searchable chunks in ChromaDB.")
print(f"4. Database folder: {DB_PATH}")
print("5. Sample IDs:", ids[:5])
print("\nNow run 06_search_chroma.py.")
