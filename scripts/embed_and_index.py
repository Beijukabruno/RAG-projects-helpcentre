#!/usr/bin/env python3
"""Embed audience-specific chunks and persist to PostgreSQL pgvector tables."""
import sys
from pathlib import Path

# Add project root to path so app module is importable
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import argparse
import hashlib
import json

from sqlalchemy import text as sql_text

from app.core.config import BATCH_SIZE, DATA_DIR, EMBEDDING_MODEL
from app.core.embeddings import embed_texts, initialize_embeddings_client
from app.core.project_manager import project_manager
from app.db.session import initialize_database, db_session_context

MODEL_NAME = EMBEDDING_MODEL


def build_index_config(project_id: str) -> dict:
    project = project_manager.get_project(project_id)
    audiences = project.get("audiences", [])
    collections = project.get("collections", {})

    cfg = {}
    for audience in audiences:
        if audience not in collections:
            raise ValueError(f"Collection not configured for audience '{audience}' in project '{project_id}'")

        chunks_path = DATA_DIR / f"{project_id}_{audience}_chunks.json"

        cfg[audience] = {
            "chunks_path": chunks_path,
            "collection_name": collections[audience],
        }
    return cfg


def _vector_to_pg_literal(vector):
    return "[" + ",".join(f"{float(v):.8f}" for v in vector) + "]"


def _text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _insert_embeddings(project_id: str, audience: str, entries: list[dict]) -> None:
    if not entries:
        return

    with db_session_context() as db:
        if db is None:
            raise RuntimeError("Database is unavailable; cannot index embeddings.")

        params = []
        for entry in entries:
            meta = entry["meta"]
            params.append(
                {
                    "chunk_id": entry["id"],
                    "project_id": project_id,
                    "audience": audience,
                    "source_file": meta.get("source_file", ""),
                    "source_name": meta.get("source_name", ""),
                    "source_url": meta.get("source_url", ""),
                    "chunk_text": entry["text"],
                    "embedding_model": MODEL_NAME,
                    "embedding": entry["embedding"],
                }
            )

        db.execute(
            sql_text(
                """
                INSERT INTO knowledge_chunk_embedding (
                    chunk_id,
                    project_id,
                    audience,
                    source_file,
                    source_name,
                    source_url,
                    chunk_text,
                    embedding_model,
                    embedding
                )
                VALUES (
                    :chunk_id,
                    :project_id,
                    :audience,
                    :source_file,
                    :source_name,
                    :source_url,
                    :chunk_text,
                    :embedding_model,
                    CAST(:embedding AS vector)
                )
                ON CONFLICT (chunk_id, project_id, audience)
                DO UPDATE SET
                    source_file = EXCLUDED.source_file,
                    source_name = EXCLUDED.source_name,
                    source_url = EXCLUDED.source_url,
                    chunk_text = EXCLUDED.chunk_text,
                    embedding_model = EXCLUDED.embedding_model,
                    embedding = EXCLUDED.embedding
                """
            ),
            params,
        )
        db.commit()


def index_audience_collection(
    audience: str,
    chunks_path: Path,
    collection_name: str,
    project_id: str,
    *,
    resume: bool = False,
):
    from tqdm import tqdm
    if not chunks_path.exists():
        raise FileNotFoundError(f"Chunks file not found for {audience}: {chunks_path}")

    with chunks_path.open('r', encoding='utf-8') as f:
        chunks = json.load(f)
    print(f"Loaded {len(chunks)} chunks for {audience} from {chunks_path}")

    entries = []
    for i, chunk in enumerate(chunks):
        chunk_body = chunk.get('text', '').strip()
        if not chunk_body:
            continue

        source_file = chunk.get('source_file', 'unknown')
        cid = f"{audience}_{source_file}_{i}"
        meta = {
            'audience': audience,
            'source_file': source_file,
            'source_name': chunk.get('source_name', ''),
            'source_url': chunk.get('source_url', ''),
        }

        entries.append(
            {
                "id": cid,
                "text": chunk_body,
                "hash": _text_hash(chunk_body),
                "meta": meta,
            }
        )

    reused_count = 0
    if resume and entries:
        with db_session_context() as db:
            if db is None:
                raise RuntimeError("Database is unavailable; cannot load existing embeddings.")
            existing_rows = db.execute(
                sql_text(
                    """
                    SELECT
                        chunk_id,
                        encode(sha256(convert_to(chunk_text, 'UTF8')), 'hex') AS sha256_hash,
                        embedding_model,
                        embedding::text AS embedding
                    FROM knowledge_chunk_embedding
                    WHERE project_id = :project_id
                      AND audience = :audience
                    """
                ),
                {"project_id": project_id, "audience": audience},
            ).mappings().all()

        existing_by_id = {row["chunk_id"]: row for row in existing_rows}
        vector_by_hash = {
            row["sha256_hash"]: row["embedding"]
            for row in existing_rows
            if row["embedding_model"] == MODEL_NAME and row["sha256_hash"]
        }

        pending = []
        reusable = []
        for entry in entries:
            existing = existing_by_id.get(entry["id"])
            if (
                existing
                and existing["embedding_model"] == MODEL_NAME
                and existing["sha256_hash"] == entry["hash"]
            ):
                continue

            reusable_embedding = vector_by_hash.get(entry["hash"])
            if reusable_embedding:
                entry["embedding"] = reusable_embedding
                reusable.append(entry)
                continue

            pending.append(entry)

        skipped_count = len(entries) - len(pending) - len(reusable)
        if reusable:
            _insert_embeddings(project_id, audience, reusable)
            reused_count = len(reusable)
        entries = pending

        if skipped_count:
            print(f"Resume enabled: skipping {skipped_count} unchanged chunks for {audience}.")
        if reused_count:
            print(f"Resume enabled: reused {reused_count} embeddings by content hash for {audience}.")

    texts = [entry["text"] for entry in entries]
    print(f"Indexing {len(texts)} chunks for {audience} in batches of {BATCH_SIZE}...")
    for start in tqdm(range(0, len(entries), BATCH_SIZE)):
        batch_entries = entries[start:start + BATCH_SIZE]
        batch_texts = [entry["text"] for entry in batch_entries]
        emb_list = embed_texts(batch_texts, model_name=MODEL_NAME, batch_size=min(BATCH_SIZE, len(batch_texts)))
        if len(emb_list) != len(batch_texts):
            raise RuntimeError(
                "Embedding count mismatch for "
                f"{project_id}/{audience} batch starting at {start}: "
                f"requested {len(batch_texts)}, received {len(emb_list)}."
            )

        rows = []
        for entry, vector in zip(batch_entries, emb_list):
            entry["embedding"] = _vector_to_pg_literal(vector)
            rows.append(entry)
        _insert_embeddings(project_id, audience, rows)

    with db_session_context() as db:
        if db is None:
            raise RuntimeError("Database is unavailable; cannot verify indexed chunk count.")
        total = db.execute(
            sql_text(
                """
                SELECT COUNT(*)
                FROM knowledge_chunk_embedding
                WHERE project_id = :project_id
                  AND audience = :audience
                """
            ),
            {"project_id": project_id, "audience": audience},
        ).scalar_one()

    print(f"Indexing complete for {audience} in logical collection '{collection_name}'.")
    print(f"Total chunk embeddings in Postgres for {project_id}/{audience}: {total}")


def main():
    parser = argparse.ArgumentParser(description="Embed and index chunk files for a project")
    parser.add_argument("--project", default="tb", help="Project ID from config/projects.yaml (default: tb)")
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip chunks that already have embeddings for the selected project/audience.",
    )
    args = parser.parse_args()

    index_config = build_index_config(args.project)

    if not initialize_database():
        raise RuntimeError("Database is unavailable; cannot continue indexing.")

    print(f"Loading embedding model via Gemini API: {MODEL_NAME}")
    initialize_embeddings_client()

    for audience, cfg in index_config.items():
        index_audience_collection(
            audience=audience,
            chunks_path=cfg["chunks_path"],
            collection_name=cfg["collection_name"],
            project_id=args.project,
            resume=args.resume,
        )

    print(f"All indexing complete for project '{args.project}'. Persisted in PostgreSQL pgvector.")

if __name__ == '__main__':
    main()
