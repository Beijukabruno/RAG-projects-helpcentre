"""
Reranker module using cross-encoder for improved relevance scoring.

This module provides reranking functionality to improve retrieval quality
by scoring query-document pairs using a cross-encoder model.
"""
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from typing import List, Tuple, Dict, Any

# Global configuration - Reranker enabled by default
RERANKER_ENABLED = True
RERANKER_MODEL_NAME = 'cross-encoder/ms-marco-MiniLM-L-6-v2'

# Global variables for lazy loading
_reranker_model = None
_tokenizer = None
_device = None


def initialize_reranker():
    """
    Initialize the reranker model and tokenizer (lazy loading).
    This is called automatically when reranking is first performed.
    """
    global _reranker_model, _tokenizer, _device
    
    if _reranker_model is not None:
        return
    
    if not RERANKER_ENABLED:
        print("[Reranker] Reranking is disabled via RERANKER_ENABLED env var")
        return
    
    print(f"[Reranker] Loading reranker model: {RERANKER_MODEL_NAME}")
    _tokenizer = AutoTokenizer.from_pretrained(RERANKER_MODEL_NAME)
    _reranker_model = AutoModelForSequenceClassification.from_pretrained(RERANKER_MODEL_NAME)
    _device = "cuda" if torch.cuda.is_available() else "cpu"
    _reranker_model.to(_device)
    _reranker_model.eval()
    print(f"[Reranker] Model loaded on device: {_device}")


def rerank_results(
    query: str,
    results: Dict[str, Any],
    top_n: int = 5
) -> Dict[str, Any]:
    """
    Rerank search results using cross-encoder scoring.
    
    Args:
        query: The user's query string
        results: ChromaDB results dict with 'ids', 'documents', 'metadatas', etc.
        top_n: Number of top results to return after reranking
    
    Returns:
        Reranked results in the same format as input results
    """
    if not RERANKER_ENABLED:
        # Return original results trimmed to top_n
        return {
            'ids': [results['ids'][0][:top_n]],
            'documents': [results['documents'][0][:top_n]],
            'metadatas': [results['metadatas'][0][:top_n]],
            'distances': [results.get('distances', [[]])[0][:top_n]]
        }
    
    # Initialize model if needed
    initialize_reranker()
    
    if _reranker_model is None:
        print("[Reranker] Model not loaded, returning original results")
        return results
    
    # Extract data from results
    ids = results.get('ids', [[]])[0]
    documents = results.get('documents', [[]])[0]
    metadatas = results.get('metadatas', [[]])[0]
    distances = results.get('distances', [[]])[0]
    
    if len(documents) == 0:
        return results
    
    # Create query-document pairs
    pairs = [(query, doc) for doc in documents]
    
    # Tokenize and prepare inputs
    inputs = _tokenizer(
        pairs,
        padding=True,
        truncation=True,
        max_length=512,
        return_tensors="pt"
    )
    inputs = {k: v.to(_device) for k, v in inputs.items()}
    
    # Get reranking scores
    with torch.no_grad():
        outputs = _reranker_model(**inputs)
        scores = outputs.logits.squeeze(-1).cpu().tolist()
    
    # Combine scores with all data
    combined = list(zip(scores, ids, documents, metadatas, distances))
    
    # Sort by score (descending)
    combined_sorted = sorted(combined, key=lambda x: x[0], reverse=True)
    
    # Take top_n
    top_results = combined_sorted[:top_n]
    
    # Reconstruct results dict
    reranked_results = {
        'ids': [[item[1] for item in top_results]],
        'documents': [[item[2] for item in top_results]],
        'metadatas': [[item[3] for item in top_results]],
        'distances': [[item[4] for item in top_results]],
        'reranker_scores': [[item[0] for item in top_results]]
    }
    
    return reranked_results


def rerank_documents_list(
    query: str,
    ids: List[str],
    documents: List[str],
    metadatas: List[Dict] = None,
    top_n: int = 5
) -> Tuple[List[str], List[str], List[Dict], List[float]]:
    """
    Rerank a list of documents and return sorted lists.
    
    Args:
        query: The user's query string
        ids: List of document IDs
        documents: List of document texts
        metadatas: Optional list of metadata dicts
        top_n: Number of top results to return
    
    Returns:
        Tuple of (reranked_ids, reranked_documents, reranked_metadatas, scores)
    """
    if not RERANKER_ENABLED:
        metadatas = metadatas or [{}] * len(documents)
        return ids[:top_n], documents[:top_n], metadatas[:top_n], []
    
    # Initialize model if needed
    initialize_reranker()
    
    if _reranker_model is None:
        metadatas = metadatas or [{}] * len(documents)
        return ids[:top_n], documents[:top_n], metadatas[:top_n], []
    
    if len(documents) == 0:
        return [], [], [], []
    
    metadatas = metadatas or [{}] * len(documents)
    
    # Create query-document pairs
    pairs = [(query, doc) for doc in documents]
    
    # Tokenize and prepare inputs
    inputs = _tokenizer(
        pairs,
        padding=True,
        truncation=True,
        max_length=512,
        return_tensors="pt"
    )
    inputs = {k: v.to(_device) for k, v in inputs.items()}
    
    # Get reranking scores
    with torch.no_grad():
        outputs = _reranker_model(**inputs)
        scores = outputs.logits.squeeze(-1).cpu().tolist()
    
    # Combine and sort
    combined = list(zip(scores, ids, documents, metadatas))
    combined_sorted = sorted(combined, key=lambda x: x[0], reverse=True)
    
    # Extract top_n
    top_results = combined_sorted[:top_n]
    
    reranked_scores = [item[0] for item in top_results]
    reranked_ids = [item[1] for item in top_results]
    reranked_documents = [item[2] for item in top_results]
    reranked_metadatas = [item[3] for item in top_results]
    
    return reranked_ids, reranked_documents, reranked_metadatas, reranked_scores
