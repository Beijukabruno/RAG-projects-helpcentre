#!/usr/bin/env python3
"""
Export all chunks from ChromaDB vector_db to a JSON file, including:
- id (actual DB id)
- text (chunk)
- source_file
- source_name
- source_url
"""
import chromadb
import json
from pathlib import Path

VECTOR_DB_PATH = Path("vector_db")
COLLECTION_NAME = "DSI_TB"
OUTPUT_PATH = Path("data/chunks_db_export.json")

client = chromadb.PersistentClient(path=str(VECTOR_DB_PATH))
collection = client.get_collection(COLLECTION_NAME)

# Get all ids in the collection
all_ids = collection.get(ids=None)["ids"]

export_chunks = []
BATCH_SIZE = 100
for start in range(0, len(all_ids), BATCH_SIZE):
    batch_ids = all_ids[start:start+BATCH_SIZE]
    batch = collection.get(ids=batch_ids)
    ids = batch["ids"]
    docs = batch["documents"]
    metas = batch["metadatas"]
    for cid, doc, meta in zip(ids, docs, metas):
        export_chunks.append({
            "id": cid,
            "text": doc,
            "source_file": meta.get("source_file", ""),
            "source_name": meta.get("source_name", ""),
            "source_url": meta.get("source_url", "")
        })

with OUTPUT_PATH.open("w", encoding="utf-8") as f:
    json.dump(export_chunks, f, ensure_ascii=False, indent=2)
print(f"Exported {len(export_chunks)} chunks from DB to {OUTPUT_PATH}")
