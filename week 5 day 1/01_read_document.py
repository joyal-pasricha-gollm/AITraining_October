"""STEP 1 — Read the source document (no AI required)."""
from rag_core import DOCUMENT_PATH, read_document

text = read_document()
print("DOCUMENT:", DOCUMENT_PATH)
print("Characters:", len(text))
print("\nFIRST 700 CHARACTERS:\n")
print(text[:700])
