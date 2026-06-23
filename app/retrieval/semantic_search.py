import logging
import os

from app.core.config import (
    EMBEDDING_MODEL,
    VECTOR_BACKEND,
    normalize_audience,
)
from app.core.embeddings import embed_query, initialize_embeddings_client
from app.core.project_manager import project_manager
from app.db.session import db_session_context
from sqlalchemy import text


logger = logging.getLogger(__name__)
RERANKER_ENABLED = os.getenv("RERANKER_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
RERETRIEVAL_K = int(os.getenv("RERETRIEVAL_K", "20"))

def _vector_to_pg_literal(vector):
    return "[" + ",".join(f"{float(v):.8f}" for v in vector) + "]"


def _search_pgvector(query_embedding, *, k: int, audience: str, project_id: str):
    if not query_embedding:
        return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

    embedding_literal = _vector_to_pg_literal(query_embedding)
    sql = text(
        """
        SELECT
            chunk_id,
            chunk_text,
            source_file,
            source_name,
            source_url,
            (embedding <=> CAST(:embedding AS vector)) AS distance
        FROM knowledge_chunk_embedding
        WHERE project_id = :project_id
          AND audience = :audience
        ORDER BY embedding <=> CAST(:embedding AS vector)
        LIMIT :top_k
        """
    )

    with db_session_context() as db:
        if db is None:
            raise RuntimeError("Database is unavailable. Semantic search requires PostgreSQL with pgvector.")

        rows = db.execute(
            sql,
            {
                "embedding": embedding_literal,
                "project_id": project_id,
                "audience": audience,
                "top_k": k,
            },
        ).mappings().all()

    ids = []
    documents = []
    metadatas = []
    distances = []
    for row in rows:
        ids.append(row["chunk_id"])
        documents.append(row["chunk_text"])
        metadatas.append(
            {
                "source_file": row.get("source_file") or "",
                "source_name": row.get("source_name") or "",
                "source_url": row.get("source_url") or "",
            }
        )
        distances.append(float(row.get("distance") or 0.0))

    return {
        "ids": [ids],
        "documents": [documents],
        "metadatas": [metadatas],
        "distances": [distances],
    }


def get_search_backend_status() -> dict:
    return {
        "vector_backend": VECTOR_BACKEND,
        "embedding_model": EMBEDDING_MODEL,
        "projects": {pid: cfg.get("collections", {}) for pid, cfg in project_manager.projects.items()},
    }


def initialize_search_backends() -> None:
    """Warm up embedding and reranker clients once at startup."""
    initialize_embeddings_client()
    from app.retrieval.reranker import initialize_reranker

    initialize_reranker()


def search(query, k=3, audience: str = "general", project_id: str = "tb"):
    from app.retrieval.reranker import rerank_results

    retrieve_k = RERETRIEVAL_K if RERANKER_ENABLED else k
    audience = normalize_audience(audience)

    embedding = embed_query(query)
    results = _search_pgvector(embedding, k=retrieve_k, audience=audience, project_id=project_id)

    if RERANKER_ENABLED:
        results = rerank_results(query, results, top_n=k)

    return results
