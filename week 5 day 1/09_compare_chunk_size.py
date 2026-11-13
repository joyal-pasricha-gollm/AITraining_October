"""Lesson 9: compare two chunk sizes without deleting the original index."""
import csv
from statistics import mean
from time import perf_counter
from rag_core import (
    COLLECTION_NAME, PROJECT_DIR, embed_texts,
    get_database, make_chunks, read_document,
)

TESTS = [
    ("How many annual leave days do full-time employees receive?", "18 days of paid annual leave"),
    ("Which days are mandatory office days?", "Tuesdays and Thursdays"),
    ("How many paid sick leave days are provided?", "eight days of paid sick leave"),
    ("When must a lost laptop be reported?", "within 24 hours"),
    ("What is the response target for a Priority 1 incident?", "within 30 minutes"),
]

client = get_database()
try:
    baseline = client.get_collection(COLLECTION_NAME, embedding_function=None)
except Exception:
    raise SystemExit("Run 05_store_in_chroma.py first, then try again.")

# Create a SECOND index. Original 180/35 collection stays untouched.
experiment_name = "brightpath_guide_100"
if experiment_name in [c.name for c in client.list_collections()]:
    client.delete_collection(experiment_name)
experiment = client.create_collection(
    experiment_name,
    embedding_function=None,
    configuration={"hnsw": {"space": "cosine"}},
)
chunks = make_chunks(read_document(), chunk_size=100, overlap=35)
experiment.add(
    ids=[f"small_{i:03d}" for i in range(1, len(chunks) + 1)],
    documents=chunks,
    embeddings=embed_texts(chunks),
)
print(f"Created experimental index: {len(chunks)} chunks (100 tokens, 35 overlap)\n")

# Embed questions once, so both indexes receive identical query vectors.
question_vectors = embed_texts([question for question, _ in TESTS])

summary = []
for label, collection in [("Baseline 180/35", baseline), ("Experiment 100/35", experiment)]:
    found_count = 0
    durations = []
    print(label)
    for (question, expected), vector in zip(TESTS, question_vectors):
        start = perf_counter()
        result = collection.query(
            query_embeddings=[vector],
            n_results=min(3, collection.count()),
            include=["documents"],
        )
        durations.append(perf_counter() - start)
        text = " ".join(result["documents"][0]).lower()
        found = expected.lower() in text
        found_count += int(found)
        print(f"  {'PASS' if found else 'FAIL'} - {question}")

    print(f"  Evidence found: {found_count}/{len(TESTS)}")
    print(f"  Average Chroma query time: {mean(durations) * 1000:.1f} ms\n")
    summary.append({
        "experiment": label,
        "chunk_count": collection.count(),
        "evidence_found_out_of_5": found_count,
        "average_query_ms": round(mean(durations) * 1000, 1),
    })

csv_path = PROJECT_DIR / "experiment_results.csv"
with csv_path.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=summary[0].keys())
    writer.writeheader()
    writer.writerows(summary)
print("Saved:", csv_path)
print("These are small demonstration samples; query times may fluctuate.")
