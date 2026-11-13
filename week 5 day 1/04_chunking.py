"""STEP 4 — Split the full document into overlapping token-based chunks."""
from rag_core import TOKENIZER, make_chunks, read_document

text = read_document()
chunks = make_chunks(text, chunk_size=180, overlap=35)
print("Total chunks:", len(chunks))
print("Chunk size: 180 tokens, overlap: 35 tokens\n")

for i, chunk in enumerate(chunks, start=1):
    print("=" * 70)
    print(f"CHUNK {i} | {len(TOKENIZER.encode(chunk))} tokens")
    print(chunk[:400] + ("..." if len(chunk) > 400 else ""))

print("\nNEXT: Run 05_store_in_chroma.py to embed and store these chunks.")
