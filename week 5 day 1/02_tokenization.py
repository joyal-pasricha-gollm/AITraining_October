"""STEP 2 — Visualize token IDs and the total token count."""
from rag_core import TOKENIZER, read_document

sentence = "Employees receive 18 days of paid annual leave."
ids = TOKENIZER.encode(sentence)
print("Sentence:", sentence)
print("Token IDs:", ids)
print("Token count:", len(ids))

print("\nTOKEN BY TOKEN:")
for token_id in ids:
    print(f"{token_id:>8} -> {TOKENIZER.decode([token_id])!r}")

full_document = read_document()
print("\nFULL DOCUMENT TOKEN COUNT:", len(TOKENIZER.encode(full_document)))
print("Note: a token is not necessarily a whole word.")
