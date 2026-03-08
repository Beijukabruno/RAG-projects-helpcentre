# Reranker Integration Guide

## Overview

The reranker improves retrieval quality in the RAG chatbot by using a **cross-encoder model** to re-score and reorder retrieved documents based on their relevance to the query.

### How It Works

1. **Initial Retrieval (Embedding Search)**: Retrieve top-N candidates (e.g., 20) using fast semantic search with sentence embeddings
2. **Reranking (Cross-Encoder Scoring)**: Score each query-document pair with a more sophisticated cross-encoder model
3. **Final Selection**: Return top-K highest-scoring documents (e.g., 5) to the LLM

### Benefits

- **Better Precision**: Cross-encoders read query + document together, capturing nuanced relevance
- **Handles Negation & Specifics**: Better at understanding "not", "without", and specific constraints
- **Reduces Hallucinations**: More relevant context = more grounded answers
- **Modest Latency**: Only scores candidates, not the entire corpus

## Configuration

### Default Settings (No Configuration Needed!)

The reranker is **enabled by default** with these hardcoded settings:

- **`RERANKER_ENABLED = True`** - Reranking is always active
- **`RERANKER_MODEL = 'cross-encoder/ms-marco-MiniLM-L-6-v2'`** - Good balance of quality and speed
- **`RERETRIEVAL_K = 20`** - Retrieves 20 candidates before reranking to top K

**No .env configuration is required.** The system works out of the box.

### Optional: Override Defaults (Advanced)

If you need to change the default behavior, you can modify the global variables in the source files:

**In `reranker.py`:**
```python
RERANKER_ENABLED = True  # Set to False to disable
RERANKER_MODEL_NAME = 'cross-encoder/ms-marco-MiniLM-L-6-v2'
```

**In `consolidated_chatbot.py` and `semantic_search.py`:**
```python
RERANKER_ENABLED = True  # Set to False to disable
RERETRIEVAL_K = 20  # Adjust retrieval pool size
```

### Model Options

Popular cross-encoder models (ranked by quality/speed trade-off):

| Model | Size | Speed | Quality | Use Case |
|-------|------|-------|---------|----------|
| `cross-encoder/ms-marco-TinyBERT-L-2-v2` | Tiny | ⚡⚡⚡ | ⭐⭐ | High-throughput |
| `cross-encoder/ms-marco-MiniLM-L-6-v2` | Small | ⚡⚡ | ⭐⭐⭐ | **Recommended default** |
| `cross-encoder/ms-marco-MiniLM-L-12-v2` | Medium | ⚡ | ⭐⭐⭐⭐ | Better quality |
| `cross-encoder/ms-marco-electra-base` | Large | 🐢 | ⭐⭐⭐⭐⭐ | Offline/batch |

## Testing Reranker Performance

### Quick Test

Run the test script to see before/after comparison:

```bash
cd /path/to/search-chatbot-tb
source .venv/bin/activate

# Test with a sample query
python scripts/test_search.py "What are the side effects of TB treatment?" 5

# Try different queries
python scripts/test_search.py "How is TB transmitted?" 5
python scripts/test_search.py "TB prevention methods" 5
```

### Output

The script shows:
- **BEFORE**: Top-5 results from embedding-only retrieval
- **AFTER**: Top-5 results after cross-encoder reranking
- **RANKING CHANGES**: Which documents moved up/down

Example output:

```
================================================================================
BEFORE vs AFTER RERANKING COMPARISON
================================================================================

🔵 BEFORE (Embedding-only Retrieval):
[1] Distance: 0.4521
    Source: WHO TB Fact Sheet
    Text: Tuberculosis (TB) is caused by bacteria...

🟢 AFTER (With Cross-Encoder Reranking):
[1] Reranker Score: 8.4523 | Embedding Distance: 0.6721
    Source: TB Treatment Guidelines
    Text: Common side effects of TB treatment include...

📊 RANKING CHANGES:
  • Rank 7 → 1: tb_treatment_guidelines_142
  • Rank 1 → 3: who_tb_factsheet_034
```

## Integration in Code

### In consolidated_chatbot.py

The reranker is automatically integrated:

```python
from reranker import rerank_results

def search(query, k=5):
    # Retrieve more candidates if reranking is enabled
    retrieve_k = RERETRIEVAL_K if RERANKER_ENABLED else k
    
    embedding = model.encode(query)
    results = collection.query(
        query_embeddings=[embedding],
        n_results=retrieve_k
    )
    
    # Apply reranking if enabled
    if RERANKER_ENABLED:
        results = rerank_results(query, results, top_n=k)
    
    return results
```

### Standalone Usage

```python
from reranker import rerank_documents_list

# Your retrieval code
query = "How is TB spread?"
ids = ["doc1", "doc2", "doc3", ...]
documents = ["text1", "text2", "text3", ...]
metadatas = [{...}, {...}, {...}, ...]

# Rerank
reranked_ids, reranked_docs, reranked_metas, scores = rerank_documents_list(
    query=query,
    ids=ids,
    documents=documents,
    metadatas=metadatas,
    top_n=5
)
```

## Performance Tuning

### Retrieval Pool Size (`RERETRIEVAL_K`)

- **Small (10-15)**: Fast, but reranker has fewer options
- **Medium (20-30)**: **Default (20)** - good balance
- **Large (50-100)**: Better coverage, higher latency

Rule of thumb: Retrieve 3-5x more than final K

### Disabling Reranker

To disable reranking and fall back to embedding-only retrieval, modify the global variable in your code:

**In `reranker.py`:**
```python
RERANKER_ENABLED = False  # Change from True to False
```

**In `consolidated_chatbot.py` and `semantic_search.py`:**
```python
RERANKER_ENABLED = False  # Change from True to False
```

Benefits of disabling:
- Faster responses (~100-200ms saved)
- Lower memory usage (no cross-encoder model)
- Simpler deployment
- Acceptable for less complex queries

## Troubleshooting

### High Memory Usage

Cross-encoders load transformer models (~100-400MB). If memory is constrained:
1. Change to smaller model in `reranker.py`: `RERANKER_MODEL_NAME = 'cross-encoder/ms-marco-TinyBERT-L-2-v2'`
2. Reduce `RERETRIEVAL_K` in your app files
3. Disable by setting `RERANKER_ENABLED = False` in the source files

### Slow First Request

The reranker model is lazy-loaded on first use. Subsequent requests are fast.

### Model Download Issues

Models are auto-downloaded from HuggingFace. If offline or behind proxy:
1. Pre-download model: `python -c "from transformers import AutoModel; AutoModel.from_pretrained('cross-encoder/ms-marco-MiniLM-L-6-v2')"`
2. Set `TRANSFORMERS_CACHE` to custom path

## Evaluation

Run the evaluation script to measure impact:

```bash
python scripts/evaluation.py
```

Expected improvements with reranking:
- **Precision@5**: +5-15%
- **NDCG@5**: +10-20%
- **Hit@5**: +5-10%
- **Latency**: +50-200ms per query

## References

- [MS MARCO Cross-Encoders](https://huggingface.co/cross-encoder)
- [Sentence Transformers Documentation](https://www.sbert.net/docs/pretrained_cross-encoders.html)
- [RAG Reranking Best Practices](https://www.pinecone.io/learn/series/rag/rerankers/)
