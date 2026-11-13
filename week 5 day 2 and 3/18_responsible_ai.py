"""DEMO 18: EY's nine Responsible AI principles applied to our RAG demo.

No API key or external package required. Prints a learning checklist.
Official EY principle labels: Accountability, Data protection, Reliability,
Security, Transparency, Explainability, Fairness, Compliance, Sustainability.
This is NOT an EY assessment or certification of compliance.
"""
from pathlib import Path
import csv
from rag_core import PROJECT_DIR, DOCUMENT_PATH

checks = [
    ("Accountability", "Who owns the RAG app and reviews failures?", "REQUIRES HUMAN OWNER"),
    ("Data protection", "Avoid sending employee identifiers to external models", "MANUAL REVIEW"),
    ("Reliability", "Run 08_benchmark_retrieval.py to compare question results", "TEST AVAILABLE"),
    ("Security", "Keep API keys out of source control", "CHECK CONFIGURATION"),
    ("Transparency", "Tell users that generated answers are AI-generated", "ADD UI DISCLOSURE"),
    ("Explainability", "Show retrieved source chunk IDs and excerpts", "DEMO AVAILABLE"),
    ("Fairness", "Compare equivalent policy questions across groups", "DEMO AVAILABLE"),
    ("Compliance", "Confirm organizational, legal and data-retention rules", "MANUAL REVIEW"),
    ("Sustainability", "Compare model/infrastructure resource needs", "MANUAL REVIEW"),
]

ignore_path = PROJECT_DIR / ".gitignore"
ignore_text = ignore_path.read_text(encoding="utf-8") if ignore_path.exists() else ""
print("Document exists:", DOCUMENT_PATH.exists())
print(".env ignored by git:", ".env" in ignore_text.splitlines())
print("\nThree governance domains: Purposeful design | Agile governance | Vigilant supervision")

for principle, check, status in checks:
    print(f"\n{principle:16} | {status}")
    print(" ", check)

output_path = PROJECT_DIR / "ey_responsible_ai_checklist.csv"
with output_path.open("w", newline="", encoding="utf-8") as file:
    writer = csv.writer(file)
    writer.writerow(["EY principle", "Classroom check", "Status"])
    writer.writerows(checks)



















