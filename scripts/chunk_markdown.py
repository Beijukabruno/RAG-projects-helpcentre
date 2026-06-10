#!/usr/bin/env python3

"""
Chunk markdown files per audience knowledge base.

Supports:
- semantic chunking (default)
- recursive chunking (fallback)

Outputs:
- data/<project>_<audience>_chunks.json
"""
import sys
from pathlib import Path

# Add project root to path so app module is importable
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import argparse
import csv
import json

from app.core.config import BASE_DIR, DATA_DIR
from app.core.embeddings import embed_query
from app.core.project_manager import project_manager


class GeminiLangChainEmbeddings:
    def embed_documents(self, texts):
        vectors = []
        for text in texts:
            vectors.append(embed_query(text))
        return vectors

    def embed_query(self, text):
        return embed_query(text)

def load_md_sources(csv_path: Path) -> dict:
    mapping = {}
    if not csv_path.exists():
        print(f"[WARN] CSV not found: {csv_path}")
        return mapping
    with csv_path.open(newline='', encoding='utf-8') as f:
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

def _build_splitter(strategy: str):
    if strategy == "semantic":
        try:
            import importlib

            SemanticChunker = importlib.import_module("langchain_experimental.text_splitter").SemanticChunker

            return SemanticChunker(
                embeddings=GeminiLangChainEmbeddings(),
                breakpoint_threshold_type="percentile",
                breakpoint_threshold_amount=90,
            )
        except Exception as exc:
            print(f"[WARN] Semantic chunking unavailable ({exc}); falling back to recursive strategy.")

    from langchain_text_splitters import RecursiveCharacterTextSplitter

    return RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100,
        add_start_index=True,
        separators=["\n\n", "\n", ".", " ", ""],
    )


def chunk_markdown_file(file_path: Path, md_sources: dict, strategy: str) -> list:

    with file_path.open(encoding='utf-8') as f:
        content = f.read().strip()
    basename = file_path.name
    meta = md_sources.get(basename, {})
    source_name = meta.get("source_name", "")
    source_url = meta.get("source_url", "")

    text_splitter = _build_splitter(strategy)
    chunks = []
    for chunk in text_splitter.create_documents([content]):
        chunks.append({
            "text": chunk.page_content,
            "source_file": basename,
            "source_name": source_name,
            "source_url": source_url
        })
    return chunks

def chunk_all_markdown(folder: Path, csv_path: Path, output_path: Path, strategy: str):
    md_sources = load_md_sources(csv_path)
    all_chunks = []
    for p in sorted(folder.glob('*.md')):
        chunks = chunk_markdown_file(p, md_sources, strategy)
        all_chunks.extend(chunks)
        print(f"Chunked: {p.name} ({len(chunks)} chunks)")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open('w', encoding='utf-8') as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)
    print(f"[DONE] Saved {len(all_chunks)} chunks to {output_path}")


def build_project_kb_config(project_id: str) -> dict:
    project = project_manager.get_project(project_id)
    audiences = project.get("audiences", [])
    kb = project.get("knowledge_base", {})
    base_path = kb.get("base_path")
    if not base_path:
        raise ValueError(f"knowledge_base.base_path missing for project '{project_id}'")

    kb_base = BASE_DIR / base_path
    # Sources live beside the audience markdown folders.
    # Example: knowledge_bases/tb/general/sources.csv

    config = {}
    for audience in audiences:
        audience_folder = kb_base / audience
        audience_csv = audience_folder / "sources.csv"
        if not audience_csv.exists():
            # Backward compatibility while migrating projects.
            audience_csv = BASE_DIR / "sources.csv"
        if not audience_csv.exists():
            # Final fallback for older TB-only layouts.
            audience_csv = BASE_DIR / "md_sources.csv"

        output_path = DATA_DIR / f"{project_id}_{audience}_chunks.json"

        config[audience] = {
            "folder": audience_folder / "md",
            "csv": audience_csv,
            "output": output_path,
        }
    return config


def main():
    parser = argparse.ArgumentParser(description="Chunk markdown files for a project")
    parser.add_argument("--project", default="tb", help="Project ID from config/projects.yaml (default: tb)")
    parser.add_argument(
        "--chunking-strategy",
        default="semantic",
        choices=["semantic", "recursive"],
        help="Chunking strategy to use (default: semantic)",
    )
    args = parser.parse_args()

    kb_config = build_project_kb_config(args.project)

    for audience, config in kb_config.items():
        folder = config["folder"]
        csv_path = config["csv"]
        output_path = config["output"]

        if not folder.exists():
            raise FileNotFoundError(f"Knowledge base folder not found for {audience}: {folder}")

        print(
            f"\n=== Building chunks for project: {args.project}, audience: {audience}, strategy: {args.chunking_strategy} ==="
        )
        chunk_all_markdown(
            folder=folder,
            csv_path=csv_path,
            output_path=output_path,
            strategy=args.chunking_strategy,
        )

if __name__ == '__main__':
    main()
