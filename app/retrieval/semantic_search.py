import logging
import os
import re
from time import perf_counter

from app.core.config import (
    CHUNKING_STRATEGY,
    EMBEDDING_MODEL,
    PERF_DEBUG,
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
HYBRID_RETRIEVAL_ENABLED = os.getenv("HYBRID_RETRIEVAL_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
HYBRID_KEYWORD_K = int(os.getenv("HYBRID_KEYWORD_K", "30"))
RRF_K = int(os.getenv("HYBRID_RRF_K", "60"))
HYBRID_WEIGHT_VECTOR = float(os.getenv("HYBRID_WEIGHT_VECTOR", "1.0"))
HYBRID_WEIGHT_KEYWORD = float(os.getenv("HYBRID_WEIGHT_KEYWORD", "1.0"))

_QUERY_TOKEN = re.compile(r"[a-z0-9]{3,}")
_FOLLOW_UP_PRONOUNS = re.compile(r"\b(it|its|they|them|that|this|those|these|he|she|his|her)\b", re.IGNORECASE)


def build_retrieval_query(user_query: str, history=None) -> str:
    query = (user_query or "").strip()
    if not query:
        return query

    tokens = query.split()
    ambiguous_followup = len(tokens) <= 8 and bool(_FOLLOW_UP_PRONOUNS.search(query))
    if ambiguous_followup and history is not None:
        last_user_message = ""
        for msg in reversed(getattr(history, "messages", [])):
            if getattr(msg, "type", "") == "human" and getattr(msg, "content", "") and getattr(msg, "content", "").strip() and getattr(msg, "content", "").strip() != query:
                last_user_message = getattr(msg, "content", "").strip()
                break

        if last_user_message:
            query = f"{last_user_message}\nFollow-up: {query}"

    lowered = query.lower()
    if re.search(r"\b(register|registered|registration|add|create|enroll)\b", lowered) and re.search(r"\b(patient|client|person|user)\b", lowered):
        expansions = [query, f"{query} register", f"{query} add", f"{query} enroll", f"{query} create"]
        return " ".join(dict.fromkeys(expansions))

    return query


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

    # Deterministic fallback: materialize the filtered subset first, then score.
    # This avoids edge cases where approximate ANN search returns no rows after
    # post-filtering by project/audience.
    sql_filtered_fallback = text(
        """
        WITH filtered AS MATERIALIZED (
            SELECT chunk_id, chunk_text, source_file, source_name, source_url, embedding
            FROM knowledge_chunk_embedding
            WHERE project_id = :project_id
              AND audience = :audience
        )
        SELECT
            chunk_id,
            chunk_text,
            source_file,
            source_name,
            source_url,
            (embedding <=> CAST(:embedding AS vector)) AS distance
        FROM filtered
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

        if not rows:
            logger.warning(
                "Primary ANN query returned 0 rows for project=%s audience=%s; using filtered fallback query.",
                project_id,
                audience,
            )
            rows = db.execute(
                sql_filtered_fallback,
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


def _search_keyword(
    query: str,
    *,
    k: int,
    audience: str,
    project_id: str,
):
    terms = _QUERY_TOKEN.findall((query or "").lower())
    if not terms:
        return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

    sql = text(
        """
        WITH ranked AS (
            SELECT
                chunk_id,
                chunk_text,
                source_file,
                source_name,
                source_url,
                ts_rank_cd(
                    to_tsvector('english', coalesce(chunk_text, '')),
                    websearch_to_tsquery('english', :query)
                 ) AS kw_rank
            FROM knowledge_chunk_embedding
            WHERE project_id = :project_id
              AND audience = :audience
              AND to_tsvector('english', coalesce(chunk_text, '')) @@ websearch_to_tsquery('english', :query)
        )
        SELECT chunk_id, chunk_text, source_file, source_name, source_url, kw_rank
        FROM ranked
        ORDER BY kw_rank DESC
        LIMIT :top_k
        """
    )

    with db_session_context() as db:
        if db is None:
            raise RuntimeError("Database is unavailable. Keyword search requires PostgreSQL.")
        rows = db.execute(
            sql,
            {
                "query": query,
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
        # Keep a distance-like field for compatibility. Higher keyword rank -> lower pseudo-distance.
        rank = float(row.get("kw_rank") or 0.0)
        distances.append(max(0.0, 1.0 - min(rank, 1.0)))

    return {
        "ids": [ids],
        "documents": [documents],
        "metadatas": [metadatas],
        "distances": [distances],
    }


def _rrf_merge(vector_results: dict, keyword_results: dict, *, top_k: int) -> dict:
    def unpack(results: dict):
        return (
            results.get("ids", [[]])[0],
            results.get("documents", [[]])[0],
            results.get("metadatas", [[]])[0],
            results.get("distances", [[]])[0],
        )

    v_ids, v_docs, v_meta, v_dist = unpack(vector_results)
    k_ids, k_docs, k_meta, k_dist = unpack(keyword_results)

    item_by_id = {}
    for cid, doc, meta, dist in list(zip(v_ids, v_docs, v_meta, v_dist)) + list(zip(k_ids, k_docs, k_meta, k_dist)):
        if cid not in item_by_id:
            item_by_id[cid] = {
                "id": cid,
                "doc": doc,
                "meta": meta,
                "dist": float(dist or 0.0),
                "score": 0.0,
            }

    for rank, cid in enumerate(v_ids, start=1):
        if cid in item_by_id:
            item_by_id[cid]["score"] += HYBRID_WEIGHT_VECTOR * (1.0 / (RRF_K + rank))

    for rank, cid in enumerate(k_ids, start=1):
        if cid in item_by_id:
            item_by_id[cid]["score"] += HYBRID_WEIGHT_KEYWORD * (1.0 / (RRF_K + rank))

    merged = sorted(item_by_id.values(), key=lambda item: item["score"], reverse=True)[:top_k]

    return {
        "ids": [[item["id"] for item in merged]],
        "documents": [[item["doc"] for item in merged]],
        "metadatas": [[item["meta"] for item in merged]],
        "distances": [[item["dist"] for item in merged]],
    }


def get_search_backend_status() -> dict:
    return {
        "vector_backend": VECTOR_BACKEND,
        "embedding_model": EMBEDDING_MODEL,
        "chunking_strategy": CHUNKING_STRATEGY,
        "perf_debug": PERF_DEBUG,
        "hybrid_retrieval_enabled": HYBRID_RETRIEVAL_ENABLED,
        "hybrid_keyword_k": HYBRID_KEYWORD_K,
        "hybrid_rrf_k": RRF_K,
        "hybrid_weight_vector": HYBRID_WEIGHT_VECTOR,
        "hybrid_weight_keyword": HYBRID_WEIGHT_KEYWORD,
        "projects": {pid: cfg.get("collections", {}) for pid, cfg in project_manager.projects.items()},
    }


def initialize_search_backends() -> None:
    """Warm up embedding and reranker clients once at startup."""
    initialize_embeddings_client()
    from app.retrieval.reranker import initialize_reranker

    initialize_reranker()


def search(query, k=3, audience: str = "general", project_id: str = "tb"):
    from app.retrieval.reranker import rerank_results

    t0 = perf_counter()
    reranker_enabled = project_manager.get_feature_flag(project_id, "reranker_enabled", default=RERANKER_ENABLED)
    retrieve_k = RERETRIEVAL_K if reranker_enabled else k
    audience = normalize_audience(audience, project_id=project_id)

    t_embed0 = perf_counter()
    embedding = embed_query(query)
    t_embed1 = perf_counter()

    t_db0 = perf_counter()
    results = _search_pgvector(embedding, k=retrieve_k, audience=audience, project_id=project_id)
    t_db1 = perf_counter()

    hybrid_enabled = project_manager.get_feature_flag(
        project_id,
        "hybrid_retrieval_enabled",
        default=HYBRID_RETRIEVAL_ENABLED,
    )
    should_hybrid = hybrid_enabled
    if should_hybrid:
        t_kw0 = perf_counter()
        keyword_results = _search_keyword(
            query,
            k=max(HYBRID_KEYWORD_K, retrieve_k),
            audience=audience,
            project_id=project_id,
        )
        results = _rrf_merge(results, keyword_results, top_k=retrieve_k)
        t_kw1 = perf_counter()
    else:
        t_kw0 = t_kw1 = perf_counter()

    if reranker_enabled:
        t_rerank0 = perf_counter()
        results = rerank_results(query, results, top_n=k, enabled=True)
        t_rerank1 = perf_counter()
    else:
        t_rerank0 = t_rerank1 = perf_counter()

    if PERF_DEBUG:
        logger.info(
            "Perf[search] project=%s audience=%s embed_ms=%.1f pg_ms=%.1f kw_ms=%.1f rerank_ms=%.1f total_ms=%.1f k=%s retrieve_k=%s reranker=%s hybrid=%s",
            project_id,
            audience,
            (t_embed1 - t_embed0) * 1000,
            (t_db1 - t_db0) * 1000,
            (t_kw1 - t_kw0) * 1000,
            (t_rerank1 - t_rerank0) * 1000,
            (perf_counter() - t0) * 1000,
            k,
            retrieve_k,
            reranker_enabled,
            should_hybrid,
        )

    return results


def retrieval_diagnostics(query: str, *, project_id: str = "tb", audience: str = "general", k: int = 8) -> dict:
    """Return retrieval-stage diagnostics without LLM generation."""
    audience = normalize_audience(audience, project_id=project_id)
    retrieve_k = max(k, RERETRIEVAL_K)
    embedding = embed_query(query)

    vector_results = _search_pgvector(embedding, k=retrieve_k, audience=audience, project_id=project_id)
    keyword_results = _search_keyword(query, k=max(HYBRID_KEYWORD_K, retrieve_k), audience=audience, project_id=project_id)
    merged_results = _rrf_merge(vector_results, keyword_results, top_k=retrieve_k)

    top_ids = merged_results.get("ids", [[]])[0][:k]
    top_meta = merged_results.get("metadatas", [[]])[0][:k]
    top_sources = [m.get("source_file", "") for m in top_meta]

    return {
        "query": query,
        "project_id": project_id,
        "audience": audience,
        "k": k,
        "vector_count": len(vector_results.get("ids", [[]])[0]),
        "keyword_count": len(keyword_results.get("ids", [[]])[0]),
        "merged_count": len(merged_results.get("ids", [[]])[0]),
        "top_chunk_ids": top_ids,
        "top_source_files": top_sources,
        "hybrid_config": {
            "enabled": project_manager.get_feature_flag(
                project_id,
                "hybrid_retrieval_enabled",
                default=HYBRID_RETRIEVAL_ENABLED,
            ),
            "keyword_k": HYBRID_KEYWORD_K,
            "rrf_k": RRF_K,
            "weight_vector": HYBRID_WEIGHT_VECTOR,
            "weight_keyword": HYBRID_WEIGHT_KEYWORD,
        },
    }
