# RAG end to end-employee guide doc 

RAG project with a fictional employee-guide document. **No LangChain, Docker, FastAPI, server, or external vector database.**


## RAG pipeline

```
Documents/BrightPath_Employee_Guide.txt
                 |
              Read text
                 |
           Token inspection
                 |
          Split into chunks
                 |
        Local embedding model
                 |
       ChromaDB / chroma_db/
                 |
      User question -> embed question
                 |
       Similarity search (top 3)
                 |
       Retrieved original chunks
                 |
         AI + context + question
                 |
        Grounded answer + sources
```


```

| Script | What to observe | What is happening |
|---|---|---|
| `01_read_document.py` | Text loaded from Documents | Python opens a local `.txt` document |
| `02_tokenization.py` | Tokens, token IDs, token count | Text is divided into tokens for inspection |
| `03_embeddings.py` | Vector length and sample values; similarity scores | A **local** embedding model converts strings into vectors |
| `04_chunking.py` | Overlapping chunks | Split the full document into **180-token chunks**, with 35-token overlap |
| `05_store_in_chroma.py` | Record count and file path | Embed each chunk; store IDs, vectors, and original text inside project-local ChromaDB |
| `06_search_chroma.py` | Top 3 source chunks and distances | Embed question and retrieve nearest stored vectors. **No AI model call** |
| `07_ask_ai.py` | Retrieved IDs and grounded answer | Send the matching chunk texts + question to OpenAI's Responses API |


### What runs where?

- The source `.txt` file: local in `Documents/`.
- Token inspection: `tiktoken` locally.
- Text embeddings: Chroma's local `all-MiniLM-L6-v2` model (384 dimensions). Chroma first downloads and caches model files; afterwards vectorization runs locally.
- Chroma database: local and persistent in `chroma_db/`.
- Question search: local vector search.
- Final generative answer: OpenAI API over the internet. **Only the retrieved context and user question are sent to the AI**, not the entire original document.
- OpenAI API usage may incur charges; it is separate from ChatGPT subscriptions.

`tiktoken`'s `cl100k_base` tokenization is educational and used for chunking; the MiniLM embedding model uses its own tokenizer internally. These tokenizations need not be identical.

## Try these questions

1. How many days of annual leave do full-time employees receive?
2. Which days are designated office days for eligible hybrid employees?
3. How quickly should a lost company laptop be reported?
4. What is the reimbursement submission deadline?
5. When must new employees complete security training?
6. What are the initial IT response targets for Priority 1 and Priority 2 incidents?
7. What are the maternity leave benefits? (Not specified — should NOT invent an answer.)
