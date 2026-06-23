import csv
import hashlib
import re
import os
import logging
import requests
from pathlib import Path
from typing import Optional, List, Dict

from fastapi import HTTPException, UploadFile
from sqlalchemy import text as sql_text

from app.core.config import BASE_DIR, BATCH_SIZE, DATA_DIR, EMBEDDING_MODEL
from app.core.embeddings import embed_texts
from app.core.project_manager import project_manager
from app.db.session import db_session_context
from app.db import admin_repo
from scripts.chunk_markdown import chunk_markdown_file, load_md_sources

logger = logging.getLogger(__name__)

MAX_FILE_BYTES = 20 * 1024 * 1024  # 20MB for PDFs


def _vector_to_pg_literal(vector):
    return "[" + ",".join(f"{float(v):.8f}" for v in vector) + "]"


def _safe_file_name(filename: str, allowed_extensions: List[str]) -> str:
    name = Path(filename).name.strip()
    name = re.sub(r"[^A-Za-z0-9._ -]+", "_", name)
    ext = Path(name).suffix.lower()
    if not name or ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"Only {', '.join(allowed_extensions)} files are supported.")
    return name


def _project_kb_base(project_id: str) -> Path:
    try:
        base_path = project_manager.get_project(project_id).get("knowledge_base", {}).get("base_path")
    except KeyError:
        base_path = f"knowledge_bases/{project_id}"
    return BASE_DIR / base_path


def _audience_dir(project_id: str, audience: str) -> Path:
    return _project_kb_base(project_id) / audience


def list_markdown_sources(project_id: str, audience: str) -> list[dict]:
    md_dir = _audience_dir(project_id, audience) / "md"
    csv_path = _audience_dir(project_id, audience) / "sources.csv"
    metadata = load_md_sources(csv_path)
    return [
        {
            "file_name": path.name,
            "source_name": metadata.get(path.name, {}).get("source_name", ""),
            "source_url": metadata.get(path.name, {}).get("source_url", ""),
            "size_bytes": path.stat().st_size,
        }
        for path in sorted(md_dir.glob("*.md"))
    ] if md_dir.exists() else []


def _validate_source_url(url: str) -> bool:
    if not url:
        return True
    if not (url.startswith("http://") or url.startswith("https://")):
        return False
    # Basic format check
    return bool(re.match(r'^https?://[^\s/$.?#].[^\s]*$', url))


def _upsert_source_csv(csv_path: Path, file_name: str, source_name: str, source_url: str | None) -> None:
    rows = []
    if csv_path.exists():
        with csv_path.open(newline="", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))

    rows = [row for row in rows if row.get("md_name") != file_name]
    rows.append(
        {
            "md_name": file_name,
            "source_name": source_name,
            "source_url": source_url or "",
        }
    )
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["md_name", "source_name", "source_url"])
        writer.writeheader()
        writer.writerows(rows)


def _remove_source_csv_row(csv_path: Path, file_name: str) -> None:
    if not csv_path.exists():
        return
    with csv_path.open(newline="", encoding="utf-8") as fh:
        rows = [row for row in csv.DictReader(fh) if row.get("md_name") != file_name]
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["md_name", "source_name", "source_url"])
        writer.writeheader()
        writer.writerows(rows)


def _record_source_asset(
    *, project_id: str, audience: str, file_name: str, source_name: str,
    source_url: str | None, checksum: str, created_by: str | None,
    status: str = "active",
) -> str:
    with db_session_context() as db:
        if db is None:
            raise RuntimeError("Database is unavailable; cannot record knowledge-base source.")
        result = db.execute(
            sql_text(
                """
                INSERT INTO source_assets (
                    project_id, audience, source_name, source_url, source_file,
                    checksum, status, created_by
                )
                VALUES (
                    :project_id, :audience, :source_name, :source_url, :source_file,
                    :checksum, :status, CAST(:created_by AS UUID)
                )
                RETURNING id
                """
            ),
            {
                "project_id": project_id,
                "audience": audience,
                "source_name": source_name,
                "source_url": source_url,
                "source_file": file_name,
                "checksum": checksum,
                "created_by": created_by,
                "status": status,
            },
        )
        asset_id = str(result.fetchone()[0])
        db.commit()
        return asset_id


def _index_chunks(project_id: str, audience: str, file_name: str, chunks: list[dict], index_run_id: Optional[str] = None) -> int:
    entries = [
        (chunk.get("text", "").strip(), chunk)
        for chunk in chunks
        if chunk.get("text", "").strip()
    ]
    if not entries:
        return 0

    total_indexed = 0
    for start in range(0, len(entries), BATCH_SIZE):
        batch_entries = entries[start:start + BATCH_SIZE]
        batch_texts = [text for text, _ in batch_entries]
        vectors = embed_texts(batch_texts, model_name=EMBEDDING_MODEL, batch_size=len(batch_texts))
        if len(vectors) != len(batch_texts):
            raise RuntimeError("Embedding count mismatch while indexing uploaded markdown.")

        with db_session_context() as db:
            if db is None:
                raise RuntimeError("Database is unavailable; cannot index knowledge-base chunks.")
            for offset, ((chunk_text, meta), vector) in enumerate(zip(batch_entries, vectors)):
                chunk_id = f"{audience}_{file_name}_{start + offset}"
                db.execute(
                    sql_text(
                        """
                        INSERT INTO knowledge_chunk_embedding (
                            chunk_id, project_id, audience, source_file, source_name,
                            source_url, chunk_text, embedding_model, embedding
                        )
                        VALUES (
                            :chunk_id, :project_id, :audience, :source_file, :source_name,
                            :source_url, :chunk_text, :embedding_model, CAST(:embedding AS vector)
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
                    {
                        "chunk_id": chunk_id,
                        "project_id": project_id,
                        "audience": audience,
                        "source_file": file_name,
                        "source_name": meta.get("source_name", ""),
                        "source_url": meta.get("source_url", ""),
                        "chunk_text": chunk_text,
                        "embedding_model": EMBEDDING_MODEL,
                        "embedding": _vector_to_pg_literal(vector),
                    },
                )
            db.commit()
        total_indexed += len(batch_entries)
        if index_run_id:
            admin_repo.update_index_run(index_run_id, "processing", chunk_count=total_indexed)
            
    return total_indexed


async def add_knowledge_source(
    *, project_id: str, audience: str, upload: UploadFile,
    source_name: str | None, source_url: str | None, actor_user_id: str | None,
) -> dict:
    """Entry point for uploading a source file (PDF, Markdown, or CSV metadata)."""
    file_name = _safe_file_name(upload.filename or "", [".md", ".pdf", ".csv"])
    content = await upload.read()
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="File is too large.")

    checksum = hashlib.sha256(content).hexdigest()
    ext = Path(file_name).suffix.lower()
    
    audience_dir = _audience_dir(project_id, audience)
    
    if ext == ".csv":
        # Handle metadata CSV upload
        try:
            reader = csv.DictReader(io.StringIO(content.decode("utf-8")))
            if not all(col in reader.fieldnames for col in ["md_name", "source_name"]):
                raise HTTPException(status_code=400, detail="CSV must contain 'md_name' and 'source_name' columns.")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid CSV format: {e}")
            
        csv_path = audience_dir / "sources.csv"
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        csv_path.write_bytes(content)
        return {
            "file_name": file_name,
            "status": "metadata_updated",
            "message": "Source metadata CSV updated successfully."
        }

    if source_url and not _validate_source_url(source_url):
        raise HTTPException(status_code=400, detail="Invalid source URL format.")

    is_pdf = ext == ".pdf"
    upload_dir = audience_dir / ("pdf" if is_pdf else "md")
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = upload_dir / file_name
    file_path.write_bytes(content)

    display_name = source_name or file_path.stem
    
    # Create ingestion job
    job_id = admin_repo.create_ingestion_job(
        project_id=project_id,
        audience=audience,
        job_type="pdf_to_md" if is_pdf else "md_upload",
        payload={"file_name": file_name, "display_name": display_name, "source_url": source_url}
    )
    
    # Record as pending asset
    asset_id = _record_source_asset(
        project_id=project_id,
        audience=audience,
        file_name=file_name,
        source_name=display_name,
        source_url=source_url,
        checksum=checksum,
        created_by=actor_user_id,
        status="pending_review"
    )
    
    return {
        "asset_id": asset_id,
        "job_id": job_id,
        "file_name": file_name,
        "status": "pending_review"
    }


def process_ingestion_job(job_id: str) -> None:
    """Background task to handle conversion and initial metadata extraction."""
    admin_repo.update_ingestion_job(job_id, "processing")
    
    with db_session_context() as db:
        if db is None:
            return
        from app.db.models import IngestionJob
        job = db.query(IngestionJob).filter(IngestionJob.id == job_id).first()
        if not job:
            return
        
        project_id = job.project_id
        audience = job.audience
        payload = job.payload
        file_name = payload["file_name"]
        
    try:
        audience_dir = _audience_dir(project_id, audience)
        if job.job_type == "pdf_to_md":
            import pymupdf4llm
            pdf_path = audience_dir / "pdf" / file_name
            md_name = Path(file_name).stem + ".md"
            md_dir = audience_dir / "md"
            md_dir.mkdir(parents=True, exist_ok=True)
            md_path = md_dir / md_name
            
            md_text = pymupdf4llm.to_markdown(str(pdf_path))
            md_path.write_text(md_text, encoding="utf-8")
            
            # Update source asset to point to the generated MD
            with db_session_context() as db:
                from app.db.models import SourceAsset
                asset = db.query(SourceAsset).filter(
                    SourceAsset.project_id == project_id,
                    SourceAsset.audience == audience,
                    SourceAsset.source_file == file_name
                ).first()
                if asset:
                    asset.source_file = md_name
                db.commit()
            
            _upsert_source_csv(audience_dir / "sources.csv", md_name, payload["display_name"], payload["source_url"])
        else:
            _upsert_source_csv(audience_dir / "sources.csv", file_name, payload["display_name"], payload["source_url"])
            
        admin_repo.update_ingestion_job(job_id, "completed", finished=True)
        
    except Exception as e:
        logger.exception(f"Failed to process ingestion job {job_id}")
        admin_repo.update_ingestion_job(job_id, "failed", error_message=str(e), finished=True)


async def activate_source(project_id: str, audience: str, asset_id: str) -> dict:
    """Approval gate: triggers indexing and marks the asset as active."""
    with db_session_context() as db:
        if db is None:
            raise RuntimeError("Database unavailable")
        from app.db.models import SourceAsset
        asset = db.query(SourceAsset).filter(SourceAsset.id == asset_id).first()
        if not asset:
            raise HTTPException(status_code=404, detail="Source asset not found")
        
        file_name = asset.source_file
        
    # Start Index Run
    run_id = admin_repo.create_index_run(
        project_id=project_id,
        audience=audience,
        embedding_model=EMBEDDING_MODEL
    )
    
    # Process indexing (could be a background task, but keeping simple for now)
    try:
        admin_repo.update_index_run(run_id, "processing")
        audience_dir = _audience_dir(project_id, audience)
        csv_path = audience_dir / "sources.csv"
        file_path = audience_dir / "md" / file_name
        
        chunks = chunk_markdown_file(file_path, load_md_sources(csv_path), strategy="recursive")
        chunk_count = _index_chunks(project_id, audience, file_name, chunks, index_run_id=run_id)
        
        admin_repo.update_index_run(run_id, "completed", chunk_count=chunk_count, finished=True)
        
        # Mark asset as active
        with db_session_context() as db:
            asset = db.query(SourceAsset).filter(SourceAsset.id == asset_id).first()
            asset.status = "active"
            db.commit()
            
        # Verify retrieval
        from app.retrieval.semantic_search import semantic_search
        search_results = semantic_search(
            query="Verify index presence",
            project_id=project_id,
            audience=audience,
            limit=1
        )
        retrieval_ok = len(search_results) > 0
            
        return {
            "asset_id": asset_id,
            "index_run_id": run_id,
            "chunk_count": chunk_count,
            "status": "active",
            "verification": {"retrieval_ok": retrieval_ok}
        }
        
    except Exception as e:
        logger.exception(f"Indexing failed for asset {asset_id}")
        admin_repo.update_index_run(run_id, "failed", error_message=str(e), finished=True)
        raise HTTPException(status_code=500, detail=f"Indexing failed: {e}")


# Legacy support for old routes if needed
async def add_markdown_source(
    *, project_id: str, audience: str, upload: UploadFile,
    source_name: str | None, source_url: str | None, actor_user_id: str | None,
) -> dict:
    # Use the new pipeline but immediately activate it (simulating old behavior)
    res = await add_knowledge_source(
        project_id=project_id, audience=audience, upload=upload,
        source_name=source_name, source_url=source_url, actor_user_id=actor_user_id
    )
    # Immediately process and activate (sync for legacy compatibility)
    if res.get("status") == "metadata_updated":
        return {"file_name": res["file_name"], "source_name": "metadata", "chunk_count": 0}
        
    process_ingestion_job(res["job_id"])
    active_res = await activate_source(project_id, audience, res["asset_id"])
    return {
        "file_name": res["file_name"],
        "source_name": source_name or res["file_name"],
        "chunk_count": active_res["chunk_count"]
    }


def remove_markdown_source(project_id: str, audience: str, file_name: str) -> dict:
    audience_dir = _audience_dir(project_id, audience)
    file_path = audience_dir / "md" / file_name
    existed = file_path.exists()
    if existed:
        file_path.unlink()
    _remove_source_csv_row(audience_dir / "sources.csv", file_name)

    with db_session_context() as db:
        if db is None:
            raise RuntimeError("Database is unavailable; cannot remove indexed chunks.")
        deleted_chunks = db.execute(
            sql_text(
                """
                DELETE FROM knowledge_chunk_embedding
                WHERE project_id = :project_id AND audience = :audience AND source_file = :source_file
                """
            ),
            {"project_id": project_id, "audience": audience, "source_file": file_name},
        ).rowcount
        db.execute(
            sql_text(
                """
                UPDATE source_assets
                SET status = 'deleted', updated_at = CURRENT_TIMESTAMP
                WHERE project_id = :project_id AND audience = :audience AND source_file = :source_file
                """
            ),
            {"project_id": project_id, "audience": audience, "source_file": file_name},
        )
        db.commit()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return {"file_name": file_name, "file_deleted": existed, "chunks_deleted": deleted_chunks}
