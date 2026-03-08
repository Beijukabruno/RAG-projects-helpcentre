#!/usr/bin/env python3
"""
Quick demo script to show reranker in action.
Runs a few example queries and shows how results improve.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import chromadb
from sentence_transformers import SentenceTransformer
from reranker import rerank_results

# Setup
BASE_DIR = Path(__file__).resolve().parents[1]
VECTOR_DB_PATH = BASE_DIR / 'vector_db'
COLLECTION_NAME = 'DSI_TB'

def run_demo():
    print("=" * 80)
    print("🚀 RERANKER DEMO - TB Knowledge Base")
    print("=" * 80)
    
    # Load resources
    print("\n📚 Loading embedding model...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    print("🔌 Connecting to ChromaDB...")
    client = chromadb.PersistentClient(path=str(VECTOR_DB_PATH))
    collection = client.get_collection(COLLECTION_NAME)
    print(f"✅ Connected! Collection has {collection.count()} documents\n")
    
    # Test queries demonstrating reranker improvements
    test_queries = [
        "What are the side effects of TB medication?",
        "How is tuberculosis transmitted between people?",
        "What is the difference between latent and active TB?",
        "How long does TB treatment take?",
    ]
    
    for i, query in enumerate(test_queries, 1):
        print("=" * 80)
        print(f"Query {i}/{len(test_queries)}: \"{query}\"")
        print("=" * 80)
        
        # Retrieve with embeddings
        query_embedding = model.encode([query]).tolist()
        results_raw = collection.query(
            query_embeddings=query_embedding,
            n_results=20,
            include=["documents", "metadatas", "distances"]
        )
        
        # Show top 3 without reranking
        print("\n🔵 Top 3 WITHOUT reranking (embedding-only):")
        for idx in range(min(3, len(results_raw['documents'][0]))):
            doc = results_raw['documents'][0][idx][:150]
            dist = results_raw['distances'][0][idx]
            source = results_raw['metadatas'][0][idx].get('source_name', 'unknown')
            print(f"  [{idx+1}] Distance: {dist:.4f} | {source}")
            print(f"      {doc}...\n")
        
        # Apply reranking
        results_reranked = rerank_results(query, results_raw, top_n=3)
        
        print("🟢 Top 3 WITH reranking (cross-encoder):")
        for idx in range(min(3, len(results_reranked['documents'][0]))):
            doc = results_reranked['documents'][0][idx][:150]
            score = results_reranked['reranker_scores'][0][idx]
            source = results_reranked['metadatas'][0][idx].get('source_name', 'unknown')
            print(f"  [{idx+1}] Score: {score:.4f} | {source}")
            print(f"      {doc}...\n")
        
        # Show ranking changes
        before_ids = results_raw['ids'][0][:3]
        after_ids = results_reranked['ids'][0][:3]
        
        if before_ids != after_ids:
            print("📊 Changes detected:")
            for j, after_id in enumerate(after_ids, 1):
                if after_id in before_ids[:3]:
                    before_rank = before_ids.index(after_id) + 1
                    if before_rank != j:
                        print(f"    • Moved from position {before_rank} → {j}")
                else:
                    # Find original position
                    if after_id in results_raw['ids'][0]:
                        original_pos = results_raw['ids'][0].index(after_id) + 1
                        print(f"    • Promoted from position {original_pos} → {j}")
        else:
            print("📊 No ranking changes (same top 3)")
        
        print()
    
    print("=" * 80)
    print("✅ Demo complete!")
    print("=" * 80)
    print("\n💡 Tips:")
    print("  • Reranker is especially good at understanding specific questions")
    print("  • It handles negation and constraints better than embeddings alone")
    print("  • Trade-off: ~100-200ms extra latency for better relevance")
    print("\n📖 See RERANKER_GUIDE.md for full documentation")

if __name__ == '__main__':
    try:
        run_demo()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure:")
        print("  1. Vector DB is indexed: python scripts/embed_and_index.py")
        print("  2. Dependencies installed: pip install -r requirements.txt")
        sys.exit(1)
