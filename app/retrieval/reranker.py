"""
Reranker module using cross-encoder for improved relevance scoring.
"""
import logging
from typing import Any, Dict, List, Tuple

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer


logger = logging.getLogger(__name__)
RERANKER_ENABLED = True
RERANKER_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"

_reranker_model = None
_tokenizer = None
_device = None


def initialize_reranker():
    global _reranker_model, _tokenizer, _device

    if _reranker_model is not None:
        return

    if not RERANKER_ENABLED:
        logger.info("Reranking disabled")
        return

    logger.info("Loading reranker model: %s", RERANKER_MODEL_NAME)
    _tokenizer = AutoTokenizer.from_pretrained(RERANKER_MODEL_NAME)
    _reranker_model = AutoModelForSequenceClassification.from_pretrained(RERANKER_MODEL_NAME)
    _device = "cuda" if torch.cuda.is_available() else "cpu"
    _reranker_model.to(_device)
    _reranker_model.eval()


def rerank_results(query: str, results: Dict[str, Any], top_n: int = 5) -> Dict[str, Any]:
    if not RERANKER_ENABLED:
        return {
            "ids": [results["ids"][0][:top_n]],
            "documents": [results["documents"][0][:top_n]],
            "metadatas": [results["metadatas"][0][:top_n]],
            "distances": [results.get("distances", [[]])[0][:top_n]],
        }

    initialize_reranker()

    if _reranker_model is None:
        return results

    ids = results.get("ids", [[]])[0]
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    if len(documents) == 0:
        return results

    pairs = [(query, doc) for doc in documents]
    inputs = _tokenizer(
        pairs,
        padding=True,
        truncation=True,
        max_length=512,
        return_tensors="pt",
    )
    inputs = {key: value.to(_device) for key, value in inputs.items()}

    with torch.no_grad():
        outputs = _reranker_model(**inputs)
        scores = outputs.logits.squeeze(-1).cpu().tolist()

    combined = list(zip(scores, ids, documents, metadatas, distances))
    combined_sorted = sorted(combined, key=lambda item: item[0], reverse=True)
    top_results = combined_sorted[:top_n]

    return {
        "ids": [[item[1] for item in top_results]],
        "documents": [[item[2] for item in top_results]],
        "metadatas": [[item[3] for item in top_results]],
        "distances": [[item[4] for item in top_results]],
        "reranker_scores": [[item[0] for item in top_results]],
    }


def rerank_documents_list(
    query: str,
    ids: List[str],
    documents: List[str],
    metadatas: List[Dict] | None = None,
    top_n: int = 5,
) -> Tuple[List[str], List[str], List[Dict], List[float]]:
    if not RERANKER_ENABLED:
        metadatas = metadatas or [{}] * len(documents)
        return ids[:top_n], documents[:top_n], metadatas[:top_n], []

    initialize_reranker()

    if _reranker_model is None or len(documents) == 0:
        metadatas = metadatas or [{}] * len(documents)
        return ids[:top_n], documents[:top_n], metadatas[:top_n], []

    metadatas = metadatas or [{}] * len(documents)
    pairs = [(query, doc) for doc in documents]
    inputs = _tokenizer(
        pairs,
        padding=True,
        truncation=True,
        max_length=512,
        return_tensors="pt",
    )
    inputs = {key: value.to(_device) for key, value in inputs.items()}

    with torch.no_grad():
        outputs = _reranker_model(**inputs)
        scores = outputs.logits.squeeze(-1).cpu().tolist()

    combined = list(zip(scores, ids, documents, metadatas))
    combined_sorted = sorted(combined, key=lambda item: item[0], reverse=True)
    top_results = combined_sorted[:top_n]

    return (
        [item[1] for item in top_results],
        [item[2] for item in top_results],
        [item[3] for item in top_results],
        [item[0] for item in top_results],
    )
