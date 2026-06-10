#!/usr/bin/env python3
"""
semantic_service/scripts/test_search.py

Run a semantic query against the service-local ChromaDB collection and
print the top-k results with document metadata.

This version shows BEFORE and AFTER reranking to demonstrate the improvement.

Usage:
  python3 scripts/test_search.py "How is TB spread?" 5
"""
import sys
import json
from pathlib import Path
import chromadb
from sentence_transformers import SentenceTransformer
import os

# Import reranker
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.retrieval.reranker import rerank_results

BASE_DIR = Path(__file__).resolve().parents[1]
VECTOR_DB_PATH = BASE_DIR / 'vector_db'
COLLECTION_NAME = 'DSI_TB'
EMBED_MODEL = os.environ.get('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
RERETRIEVAL_K = 20  # Retrieve more candidates for reranking

print(f"[DEBUG] VECTOR_DB_PATH: {VECTOR_DB_PATH.resolve()}")
print(f"[DEBUG] COLLECTION_NAME: {COLLECTION_NAME}")


def load_model():
    print(f"Loading embedding model: {EMBED_MODEL}")
    return SentenceTransformer(EMBED_MODEL)


def connect_chromadb():
    print(f"Connecting to ChromaDB at '{VECTOR_DB_PATH}'...")
    client = chromadb.PersistentClient(path=str(VECTOR_DB_PATH))
    try:
        collection = client.get_collection(COLLECTION_NAME)
        print(f"Connected to collection '{COLLECTION_NAME}' ({collection.count()} records)")
    except Exception:
        print(f"Collection '{COLLECTION_NAME}' not found, creating a new one.")
        collection = client.get_or_create_collection(COLLECTION_NAME)
    return collection

def run_query(model, collection, query_text, top_k=5, retrieve_k=None):
    """
    Run a query and return formatted results.
    
    Args:
        model: Embedding model
        collection: ChromaDB collection
        query_text: Query string
        top_k: Number of results to return
        retrieve_k: Number of candidates to retrieve (defaults to top_k)
    """
    if retrieve_k is None:
        retrieve_k = top_k
        
    print(f"\nRunning query: \"{query_text}\" (retrieving {retrieve_k}, showing top {top_k})")
    query_embedding = model.encode([query_text])
    try:
        emb_list = query_embedding.tolist()
    except Exception:
        emb_list = query_embedding

    results = collection.query(
        query_embeddings=emb_list,
        n_results=retrieve_k,
        include=["documents", "metadatas", "distances"],
    )

    # Limit to top_k if needed
    docs = results.get("documents", [[]])[0][:top_k]
    metas = results.get("metadatas", [[]])[0][:top_k]
    dists = results.get("distances", [[]])[0][:top_k]
    ids = results.get("ids", [[]])[0][:top_k]
    
    formatted = []
    for doc, meta, dist, cid in zip(docs, metas, dists, ids):
        formatted.append({
            "doc_id": cid,
            "full_text": doc,
            "chunk_size": len(doc),
            "distance": round(dist, 4),
            "source_file": meta.get("source_file", ""),
            "source_name": meta.get("source_name", ""),
            "source_url": meta.get("source_url", "")
        })
    return formatted, results

def run_query_with_reranking(model, collection, query_text, top_k=5, retrieve_k=RERETRIEVAL_K):
    """
    Run a query with reranking.
    
    Args:
        model: Embedding model
        collection: ChromaDB collection
        query_text: Query string
        top_k: Number of final results after reranking
        retrieve_k: Number of candidates to retrieve before reranking
    """
    print(f"\n🔍 Running query with RERANKING: \"{query_text}\"")
    print(f"   → Retrieving {retrieve_k} candidates, reranking to top {top_k}")
    
    query_embedding = model.encode([query_text])
    try:
        emb_list = query_embedding.tolist()
    except Exception:
        emb_list = query_embedding

    # Get more candidates
    results = collection.query(
        query_embeddings=emb_list,
        n_results=retrieve_k,
        include=["documents", "metadatas", "distances"],
    )

    # Apply reranking
    reranked_results = rerank_results(query_text, results, top_n=top_k)
    
    # Format results
    docs = reranked_results.get("documents", [[]])[0]
    metas = reranked_results.get("metadatas", [[]])[0]
    dists = reranked_results.get("distances", [[]])[0]
    ids = reranked_results.get("ids", [[]])[0]
    scores = reranked_results.get("reranker_scores", [[]])[0]
    
    formatted = []
    for i, (doc, meta, dist, cid, score) in enumerate(zip(docs, metas, dists, ids, scores)):
        formatted.append({
            "rank": i + 1,
            "doc_id": cid,
            "full_text": doc,
            "chunk_size": len(doc),
            "embedding_distance": round(dist, 4),
            "reranker_score": round(score, 4),
            "source_file": meta.get("source_file", ""),
            "source_name": meta.get("source_name", ""),
            "source_url": meta.get("source_url", "")
        })
    return formatted

def print_comparison(query_text, before_results, after_results):
    """Print side-by-side comparison of results."""
    print("\n" + "="*80)
    print("BEFORE vs AFTER RERANKING COMPARISON")
    print("="*80)
    print(f"Query: \"{query_text}\"\n")
    
    print("🔵 BEFORE (Embedding-only Retrieval):")
    print("-" * 80)
    for i, result in enumerate(before_results, 1):
        print(f"\n[{i}] Distance: {result['distance']}")
        print(f"    Source: {result['source_name'] or result['source_file']}")
        print(f"    Text: {result['full_text'][:200]}...")
    
    print("\n" + "="*80)
    print("🟢 AFTER (With Cross-Encoder Reranking):")
    print("-" * 80)
    for i, result in enumerate(after_results, 1):
        print(f"\n[{i}] Reranker Score: {result['reranker_score']:.4f} | Embedding Distance: {result['embedding_distance']}")
        print(f"    Source: {result['source_name'] or result['source_file']}")
        print(f"    Text: {result['full_text'][:200]}...")
    
    print("\n" + "="*80)
    print("📊 RANKING CHANGES:")
    print("-" * 80)
    
    # Compare doc_ids to see which documents moved
    before_ids = [r['doc_id'] for r in before_results]
    after_ids = [r['doc_id'] for r in after_results]
    
    for i, after_id in enumerate(after_ids, 1):
        if after_id in before_ids:
            before_rank = before_ids.index(after_id) + 1
            if before_rank != i:
                print(f"  • Rank {before_rank} → {i}: {after_id}")
        else:
            print(f"  • NEW at rank {i}: {after_id} (was ranked >{len(before_results)})")
    
    # Check for documents that dropped out
    for before_id in before_ids:
        if before_id not in after_ids:
            before_rank = before_ids.index(before_id) + 1
            print(f"  • DROPPED from rank {before_rank}: {before_id}")
    
    print("="*80)

def main():
    query_text = sys.argv[1] if len(sys.argv) > 1 else "How is TB spread?"
    top_k = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    model = load_model()
    collection = connect_chromadb()
    
    # Run BEFORE (without reranking)
    print("\n" + "="*80)
    print("PHASE 1: Standard Embedding Retrieval (BEFORE)")
    print("="*80)
    before_results, _ = run_query(model, collection, query_text, top_k)
    
    # Run AFTER (with reranking)
    print("\n" + "="*80)
    print("PHASE 2: Retrieval + Cross-Encoder Reranking (AFTER)")
    print("="*80)
    after_results = run_query_with_reranking(model, collection, query_text, top_k, RERETRIEVAL_K)
    
    # Print comparison
    print_comparison(query_text, before_results, after_results)
    
    # Also save JSON output
    output = {
        "query": query_text,
        "before_reranking": before_results,
        "after_reranking": after_results
    }
    
    print("\n📄 JSON Output:")
    print(json.dumps(output, indent=2))

if __name__ == '__main__':
    main()
