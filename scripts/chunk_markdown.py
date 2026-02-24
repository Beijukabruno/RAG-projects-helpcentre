#!/usr/bin/env python3

"""
Chunk markdown files in the `mds/` directory into character-based chunks using RecursiveCharacterTextSplitter.
Saves output as `data/chunks.json`. Metadata is loaded from md_sources.csv.
"""
import os
import csv
import json
from pathlib import Path
# from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_text_splitters import RecursiveCharacterTextSplitter

BASE_DIR = Path(__file__).resolve().parents[1]
MDS_DIR = BASE_DIR / "mds"
CSV_PATH = BASE_DIR / "md_sources.csv"
OUTPUT_PATH = BASE_DIR / "data" / "chunks.json"

def load_md_sources(csv_path: str = str(CSV_PATH)) -> dict:
    mapping = {}
    p = Path(csv_path)
    if not p.exists():
        print(f"[WARN] CSV not found: {csv_path}")
        return mapping
    with p.open(newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            md = row.get("md_name", "").strip()
            source_name = (row.get("source_name") or "").strip()
            source_url = (row.get("source_url") or "").strip()
            if md:
                mapping[md] = {
                    "source_name": source_name,
                    "source_url": source_url
                }
    return mapping

def chunk_markdown_file(file_path: Path, md_sources: dict) -> list:
    with file_path.open(encoding='utf-8') as f:
        content = f.read().strip()
    basename = file_path.name
    meta = md_sources.get(basename, {})
    source_name = meta.get("source_name", "")
    source_url = meta.get("source_url", "")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100,
        add_start_index=True,
        separators=["\n\n", "\n", ".", " ", ""]
    )
    chunks = []
    for chunk in text_splitter.create_documents([content]):
        chunks.append({
            "text": chunk.page_content,
            "source_file": basename,
            "source_name": source_name,
            "source_url": source_url
        })
    return chunks

def chunk_all_markdown(folder: Path = MDS_DIR, output_path: Path = OUTPUT_PATH):
    md_sources = load_md_sources()
    all_chunks = []
    for p in sorted(folder.glob('*.md')):
        chunks = chunk_markdown_file(p, md_sources)
        all_chunks.extend(chunks)
        print(f"Chunked: {p.name} ({len(chunks)} chunks)")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open('w', encoding='utf-8') as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)
    print(f"[DONE] Saved {len(all_chunks)} chunks to {output_path}")

if __name__ == '__main__':
    chunk_all_markdown()
