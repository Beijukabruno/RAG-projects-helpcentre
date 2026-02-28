#!/usr/bin/env python3
"""
Script to add a unique chunk ID to each entry in chunks.json and save to a new file (e.g., chunks_with_id.json).
The ID format will be: <source_file>_<index> (matching the embedding/indexing logic).
"""
import json
from pathlib import Path

INPUT_PATH = Path("data/chunks.json")
OUTPUT_PATH = Path("data/chunks_with_id.json")

def main():
    with INPUT_PATH.open("r", encoding="utf-8") as f:
        chunks = json.load(f)
    new_chunks = []
    for i, chunk in enumerate(chunks):
        source_file = chunk.get("source_file", "unknown")
        chunk_id = f"{source_file}_{i}"
        chunk_with_id = dict(chunk)
        chunk_with_id["id"] = chunk_id
        new_chunks.append(chunk_with_id)
    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(new_chunks, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(new_chunks)} chunks with IDs to {OUTPUT_PATH}")

if __name__ == "__main__":
    main()
