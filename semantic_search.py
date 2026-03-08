from sentence_transformers import SentenceTransformer
import chromadb
import os
from pathlib import Path
from reranker import rerank_results

BASE_DIR = Path(__file__).resolve().parent
model_name = os.environ.get('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
print(f"Loading embedding model: {model_name}")
model = SentenceTransformer(model_name)
persist_directory = str(BASE_DIR / "vector_db")
client = chromadb.PersistentClient(path=persist_directory)
collection = client.get_or_create_collection(name="DSI_TB")

# Reranker configuration - enabled by default
RERANKER_ENABLED = True
RERETRIEVAL_K = 20


def search(query, k=3):
    """
    Search with optional reranking.
    If reranking is enabled, retrieves more candidates then reranks.
    """
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


if __name__ == "__main__":
    user_query = "What are the side effects of TB treatment?"
    results = search(user_query)
    for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
        print(f"Text: {doc}\nSource: {meta['source_file']}\nSection: {meta['header']}\n")
