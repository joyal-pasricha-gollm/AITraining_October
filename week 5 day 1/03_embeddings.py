"""STEP 3 — Turn text into vectors and compare semantic similarity."""
from math import sqrt
from rag_core import embed_texts

sentences = [
    "How much annual leave do employees receive?",
    "Full-time employees get 18 days of paid annual leave.",
    "newton discovered gravity.",
]

vectors = embed_texts(sentences)
print("Embeddings are arrays of numbers representing meaning.\n")
for sentence, vector in zip(sentences, vectors):
    print("Text:", sentence)
    print("Vector dimension:", len(vector))
    print("First 8 vector values:", [round(x, 4) for x in vector[:8]], "\n")


def cosine_similarity(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    length_a = sqrt(sum(x * x for x in a))
    length_b = sqrt(sum(y * y for y in b))
    return dot / (length_a * length_b)


print("Semantic similarity with the question:")
print("Relevant leave sentence:", round(cosine_similarity(vectors[0], vectors[1]), 3))
print("Unrelated laptop sentence:", round(cosine_similarity(vectors[0], vectors[2]), 3))
print("The model runs locally. First use may download the model (~80 MB).")
