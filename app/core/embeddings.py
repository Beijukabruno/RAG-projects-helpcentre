import logging
import hashlib
import os
import re
import math
from typing import Iterable, List

from dotenv import load_dotenv

from app.core.config import EMBEDDING_DIM, EMBEDDING_MODEL


load_dotenv()
logger = logging.getLogger(__name__)

_embedding_client = None
_batch_embedding_supported = None


_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]+")


def _get_client():
    global _embedding_client
    if _embedding_client is not None:
        return _embedding_client

    import google.genai as genai

    api_key = os.getenv("GEMMA_API_KEY")
    if not api_key or api_key == "your_gemma_api_key_here":
        raise ValueError("GEMMA_API_KEY environment variable is not set or is using placeholder value")

    _embedding_client = genai.Client(api_key=api_key)
    return _embedding_client


def initialize_embeddings_client() -> None:
    try:
        _get_client()
    except Exception as exc:
        logger.warning("Embedding client not initialized at startup: %s", exc)


def _batched(values: List[str], batch_size: int) -> Iterable[List[str]]:
    for idx in range(0, len(values), batch_size):
        yield values[idx : idx + batch_size]


def _fallback_embedding(text: str) -> List[float]:
    vector = [0.0] * EMBEDDING_DIM
    tokens = _TOKEN_PATTERN.findall(text.lower())
    if not tokens:
        tokens = [text.lower().strip() or "empty"]

    for position, token in enumerate(tokens):
        digest = hashlib.sha256(f"{position}:{token}".encode("utf-8")).digest()
        bucket = int.from_bytes(digest[:4], "big") % EMBEDDING_DIM
        weight = (int.from_bytes(digest[4:8], "big") / 2**32) * 2.0 - 1.0
        vector[bucket] += weight

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def embed_texts(texts: List[str], *, model_name: str | None = None, batch_size: int = 64) -> List[List[float]]:
    global _batch_embedding_supported

    model = model_name or EMBEDDING_MODEL
    normalized = [str(text or "").strip() for text in texts if str(text or "").strip()]
    if not normalized:
        return []

    try:
        client = _get_client()
    except Exception as exc:
        logger.warning("Embedding client unavailable; using local fallback vectors: %s", exc)
        return [_fallback_embedding(text) for text in normalized]

    vectors: List[List[float]] = []

    for chunk in _batched(normalized, batch_size):
        try:
            if _batch_embedding_supported is not False:
                result = client.models.embed_content(
                    model=model,
                    contents=chunk,
                    config={"output_dimensionality": EMBEDDING_DIM},
                )

                chunk_embeddings = [list(item.values) for item in getattr(result, "embeddings", [])]

                if len(chunk_embeddings) == len(chunk):
                    _batch_embedding_supported = True
                    vectors.extend(chunk_embeddings)
                    continue

                _batch_embedding_supported = False
                logger.warning(
                    "Embedding batch cardinality mismatch (requested=%s, received=%s). Falling back to per-text embedding.",
                    len(chunk),
                    len(chunk_embeddings),
                )

            for text in chunk:
                try:
                    single = client.models.embed_content(
                        model=model,
                        contents=text,
                        config={"output_dimensionality": EMBEDDING_DIM},
                    )
                    single_embeddings = [list(item.values) for item in getattr(single, "embeddings", [])]
                    if not single_embeddings:
                        raise RuntimeError("Embedding API returned no vectors for input text.")
                    vectors.append(single_embeddings[0])
                except Exception as exc:
                    logger.warning("Embedding request failed; using local fallback vector for one text: %s", exc)
                    vectors.append(_fallback_embedding(text))
        except Exception as exc:
            logger.warning("Embedding request failed; using local fallback vectors for this batch: %s", exc)
            vectors.extend(_fallback_embedding(text) for text in chunk)

    return vectors


def embed_query(query: str, *, model_name: str | None = None) -> List[float]:
    values = embed_texts([query], model_name=model_name, batch_size=1)
    if not values:
        return []
    return values[0]
