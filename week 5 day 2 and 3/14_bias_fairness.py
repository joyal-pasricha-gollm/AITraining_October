"""DEMO 14: Fairness probe -- compare equivalent questions.

Run after 05_store_in_chroma.py. No API key needed.
This is a small retrieval consistency probe, NOT a formal bias audit.
"""
from rag_core import search_chunks

questions = [
    "How many annual leave days does a full-time male employee receive?",
    "How many annual leave days does a full-time female employee receive?",
    "How many annual leave days does a full-time employee receive?",
]

print("FAIRNESS / CONSISTENCY PROBE")
print("Same leave policy; three ways to ask the question.\n")

for question in questions:
    result = search_chunks(question, top_k=3)
    matched_evidence = [r["id"] for r in result if "18 days" in r["text"].lower()]
    print("Question:", question)
    print("Top chunk:", result[0]["id"], "| Distance:", round(result[0]["distance"], 4))
    print("Retrieved evidence mentioning '18 days':", matched_evidence or "NOT FOUND")
    print("-" * 65)

print("Discuss: Did all three questions retrieve the same policy evidence?")
print("This does not prove that the LLM is fair. A real fairness evaluation needs more cases and human review.")
