"""DEMO 16: Show why RAG returned an answer: source trace + cosine distance.

No paid API needed. This is evidence traceability, not an explanation of LLM internals.
"""
from rag_core import search_chunks

question = "How many annual leave days do full-time employees receive?"
results = search_chunks(question, top_k=3)

print("QUESTION:", question)
print("\nRETRIEVAL EVIDENCE (smaller cosine distance = closer match)")
for rank, item in enumerate(results, start=1):
    print("\n", rank, ". Source ID: ", item["id"], sep="")
    print("Document:", item["source"])
    print("Cosine distance:", round(item["distance"], 4))
    # Show a compact window around the sentence of interest, if present.
    text = " ".join(item["text"].split())
    marker = "Full-time employees receive"
    pos = text.lower().find(marker.lower())
    if pos >= 0:
        excerpt = text[max(0, pos - 25):pos + 170]
    else:
        excerpt = text[:180]
    print("Evidence:", excerpt + ("..." if len(text) > 180 else ""))