# search-chatbot-dsi-tb

This repository hosts an audience-aware Help Centre service for `general` and `clinicians` audiences.
It provides a modular API for chatbot answers and semantic retrieval that can be extended to multiple projects (TB, cervical cancer, maternal health, ...).

## Repository structure

- `app/`: main FastAPI package
- `app/api/routes/`: chat, search, health, feedback, and admin routes
- `app/core/`: configuration, logging, prompts, chat history, guardrails, and LLM helpers
- `app/retrieval/`: semantic retrieval and reranking
- `app/db/`: database models, session handling, and persistence helpers
- `knowledge_bases/`: audience-specific markdown sources and source CSVs
- `data/`: generated chunk JSON files
- `vector_db/`: generated Chroma persistence
- `interfaces/`: Streamlit, Gradio, and chat UI clients
- `deploy/`: Docker and deployment assets
- `scripts/`: chunking, embedding, and utility scripts
- `tests/`: smoke tests for API and retrieval logic

## Runtime flow

1. Markdown content is chunked with `scripts/chunk_markdown.py`.
2. Chunks are embedded and indexed into `vector_db/` with `scripts/embed_and_index.py`.
3. FastAPI serves:
   - `/chat/general`
   - `/chat/clinicians`
   - `/api/search/general`
   - `/api/search/clinicians`
4. Retrieval uses audience-specific Chroma collections and an optional reranker.
5. Database persistence is optional. If Postgres is unavailable, the API still runs and logs the DB status clearly.

## Defaults

- Chat and semantic search use `k = 5` by default.
- Unknown audience values fall back to `general`.
- The API can start without Postgres; persistence degrades gracefully.

## Running locally

Install dependencies:

```bash
python3 -m pip install --upgrade pip
pip install -r requirements.txt
```

API:

```bash
python3 -m uvicorn app.main:app --reload
```

Chunk + index rebuild:

```bash
python3 scripts/chunk_markdown.py
python3 scripts/embed_and_index.py
```

Semantic-only API:

```bash
python3 -m uvicorn semantic_app:app --reload
```

Streamlit UI:

```bash
streamlit run interfaces/streamlit/app.py
```

Gradio UI:

```bash
python3 interfaces/gradio/app.py
```

## Deployment

Deployment files now live under:

- `deploy/docker/Dockerfile`
- `deploy/docker/docker-compose.yml`
- `deploy/scripts/entrypoint.sh`
- `deploy/scripts/healthcheck.sh`

The GitHub Actions workflow at `.github/workflows/deploy_to_vm.yml` now:

1. installs dependencies
2. runs tests
3. builds the image from `deploy/docker/Dockerfile`
4. copies `deploy/docker/docker-compose.yml` to the VM
5. deploys using the new deployment path layout

## Knowledge base layout

- `knowledge_bases/general/md`
- `knowledge_bases/general/sources.csv`
- `knowledge_bases/clinicians/md`
- `knowledge_bases/clinicians/sources.csv`

## Tests

```bash
python3 -m pytest tests
```

## Vector Database Structure

The vector database is built in two stages:

1. `scripts/chunk_markdown.py`
2. `scripts/embed_and_index.py`

### Step 1: Chunk creation

The chunking script reads the audience-specific markdown files from:

- `knowledge_bases/general/md`
- `knowledge_bases/clinicians/md`

It also reads the matching source metadata from:

- `knowledge_bases/general/sources.csv`
- `knowledge_bases/clinicians/sources.csv`

Each markdown file is split with `RecursiveCharacterTextSplitter` using:

- `chunk_size = 1000`
- `chunk_overlap = 100`

For each chunk, the script stores:

- `text`
- `source_file`
- `source_name`
- `source_url`

The generated chunk files are written to:

- `data/general_chunks.json`
- `data/clinicians_chunks.json`

### Step 2: Embedding and indexing

The indexing script loads the generated chunk JSON files, creates embeddings with the configured sentence-transformer model, and writes them into ChromaDB under `vector_db/`.

By default, the embedding model is:

- `all-MiniLM-L6-v2`

The script creates one Chroma collection per audience:

- `DSI_TB_GENERAL`
- `DSI_TB_CLINICIANS`

Each stored vector record contains:

- `id`
- `embedding`
- `document`
- `metadata`

The ID format is:

- `{audience}_{source_file}_{index}`

Example:

- `general_FAQ.md_12`
- `clinicians_01-doctor-user-manual.md_4`

The metadata stored with each vector includes:

- `audience`
- `source_file`
- `source_name`
- `source_url`

### How retrieval works

At runtime:

1. the API selects the audience collection
2. the user query is embedded with the same embedding model
3. Chroma returns the top semantic matches
4. the reranker optionally reorders the retrieved candidates
5. the API returns the best `k` results

If an audience-specific collection returns nothing, the system can fall back to the legacy collection `DSI_TB`.

### Why this structure is useful

- It keeps `general` and `clinicians` content separated.
- It allows audience-aware retrieval without mixing user-facing and clinical guidance.
- It preserves source metadata so the interface can show trusted supporting documents.
- It supports rebuilding the vector database whenever the knowledge base changes.

## Presentation Summary

Here is a short summary you can use to present the work done:

This project was reorganized into a cleaner, production-friendly structure with a dedicated FastAPI application package, clearer deployment assets, separated knowledge bases, and organized interfaces. The retrieval pipeline now supports audience-aware search for both general users and clinicians, using a Chroma-based vector database with source-linked semantic retrieval and reranking.

The API was improved to degrade gracefully when Postgres is unavailable, so the service can still run even when persistence is down. Retrieval also now exits early when no relevant chunks are found, which reduces unnecessary downstream work and avoids avoidable LLM calls.

On the user experience side, the interface was redesigned into a search-first AI experience that presents a cleaner AI overview and supporting sources without exposing low-level system details. The answer flow is grounded by retrieval, while the source panel keeps the evidence visible and easier to trust.

Overall, the work improved maintainability, deployment readiness, resilience, retrieval quality, and user-facing clarity.
