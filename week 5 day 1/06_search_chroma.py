"""STEP 6 — Search the saved ChromaDB without asking an AI model."""
from rag_core import search_chunks

print("Ask questions about the employee guide. Type exit to stop.")
while True:
    question = input("\nSearch question: ").strip()
    if question.lower() in {"exit", "quit"}:
        break
    if not question:
        continue
    try:
        matches = search_chunks(question, top_k=3)
    except RuntimeError as error:
        print(error)
        break

    print("\nTOP MATCHING CHUNKS (smaller cosine distance = closer):")
    for match in matches:
        print("\n" + "=" * 72)
        print(f"ID: {match['id']} | Distance: {match['distance']:.4f}")
        print("Source:", match["source"])
        print(match["text"])
