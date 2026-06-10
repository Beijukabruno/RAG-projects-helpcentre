# Current Implementation Overview

## Purpose

This document explains the current implementation of the Help Centre chatbot service. It is written as a presentation-ready breakdown of the application architecture, retrieval pipeline, database structure, and indexing workflow.

The current system is a multi-project, audience-aware RAG service built with FastAPI, Gemini/Gemma models, PostgreSQL, and pgvector.

## High-Level Summary

The application accepts user questions, retrieves relevant knowledge-base chunks using semantic search, sends the retrieved context to an LLM, and returns a grounded answer with source metadata.

Current core capabilities:

- project-specific chat and search endpoints
- separate audiences for `general` and `clinicians`
- Gemini embedding generation
- PostgreSQL vector search using `pgvector`
- reranking with a cross-encoder model
- Gemma/Gemini LLM answer generation
- input and output guardrails
- chat, source, toxicity, and feedback persistence
- project registry synchronization into PostgreSQL

## Supported Projects

Projects are configured in [config/projects.yaml](../config/projects.yaml).

Currently configured projects:

- `tb`
- `cervical_cancer`
- `maternal_health`

Each project supports two audiences:

- `general`
- `clinicians`

The audience is important because each audience can have different source material, retrieval results, and response style.

## Main Application Structure

The FastAPI entrypoint is [app/main.py](../app/main.py).

Main application layers:

- [app/api/routes](../app/api/routes): HTTP routes for chat, search, feedback, health, and admin diagnostics
- [app/core](../app/core): configuration, embeddings, LLM client, prompts, guardrails, and project registry
- [app/retrieval](../app/retrieval): semantic search and reranking
- [app/db](../app/db): database connection, schema bootstrap, ORM models, and persistence helpers
- [scripts](../scripts): chunking, embedding, indexing, project synchronization, and utility scripts
- [db_schema.sql](../db_schema.sql): production database schema

## Runtime Startup Flow

When the FastAPI app starts, [app/main.py](../app/main.py) runs startup initialization.

Startup steps:

1. Load environment variables.
2. Configure logging.
3. Connect to PostgreSQL.
4. Apply required database extensions.
5. Apply [db_schema.sql](../db_schema.sql).
6. Create ORM-backed chat tables if needed.
7. Initialize embedding and reranker clients.
8. Initialize guardrails.
9. Initialize the GenAI client for LLM calls.

The database bootstrap logic is implemented in [app/db/session.py](../app/db/session.py).

## Configuration

Runtime settings are defined in [app/core/config.py](../app/core/config.py).

Important current defaults:

```python
EMBEDDING_MODEL = "models/gemini-embedding-2"
EMBEDDING_PROVIDER = "gemini"
EMBEDDING_DIM = 1536
VECTOR_BACKEND = "postgres"
BATCH_SIZE = 64
```

The application now expects PostgreSQL with the `pgvector` extension for semantic search.

The main database setting is:

```python
DATABASE_URL
```

Default value:

```text
postgresql://helpcentre_user:helpcentre_pass@postgres_helpcentre:5432/helpcentre_db
```

## Project Registry

The project registry is managed by [app/core/project_manager.py](../app/core/project_manager.py).

It reads [config/projects.yaml](../config/projects.yaml), which defines:

- project IDs
- enabled audiences
- collection names
- knowledge-base paths
- LLM model settings
- project-specific prompt rules

Example project shape:

```yaml
projects:
  tb:
    audiences: [general, clinicians]
    collections:
      general: TB_GENERAL
      clinicians: TB_CLINICIANS
    knowledge_base:
      base_path: knowledge_bases/tb
    llm:
      model: gemma-4-31b-it
      system_role: "TB expert"
      prompt_rules:
        - "Prioritize Ministry of Health guidance, WHO, CDC, and when present."
```

Important note:

The runtime still reads the YAML file directly for project behavior. The database project registry is synchronized from this YAML using [scripts/sync_projects_to_db.py](../scripts/sync_projects_to_db.py).

## API Routes

The service exposes project-specific routes. These are preferred over the older generic routes.

### Chat Routes

Project-scoped chat routes:

- `POST /tb/chat/general`
- `POST /tb/chat/clinicians`
- `POST /cervical_cancer/chat/general`
- `POST /cervical_cancer/chat/clinicians`
- `POST /maternal_health/chat/general`
- `POST /maternal_health/chat/clinicians`

Legacy chat routes still exist:

- `POST /chat`
- `POST /chat/general`
- `POST /chat/clinicians`

### Search Routes

Project-scoped search routes:

- `POST /tb/search/general`
- `POST /tb/search/clinicians`
- `POST /cervical_cancer/search/general`
- `POST /cervical_cancer/search/clinicians`
- `POST /maternal_health/search/general`
- `POST /maternal_health/search/clinicians`

Legacy search routes still exist:

- `POST /search`
- `POST /search/general`
- `POST /search/clinicians`

### Feedback Routes

Project-scoped feedback routes:

- `POST /tb/feedback/rate`
- `POST /cervical_cancer/feedback/rate`
- `POST /maternal_health/feedback/rate`

Legacy feedback route:

- `POST /rate`

### Health Routes

- `GET /health`
- `GET /ready`

`/ready` returns database status and search backend status.

## Chat Request Flow

The chat flow is implemented in [app/api/routes/chat.py](../app/api/routes/chat.py).

Flow:

```text
User query
-> route determines project_id and audience
-> normalize audience
-> validate project exists
-> input guardrail
-> semantic search
-> prompt builder
-> LLM call
-> output guardrail
-> persist chat exchange
-> return answer and sources
```

If the input guardrail blocks the query, the app returns a safe response and stores the exchange.

If semantic search finds no chunks, the app returns:

```text
Sorry, I could not find any relevant information for your question.
```

If the LLM call succeeds, the app stores:

- user message
- assistant answer
- prompt sent to the LLM
- LLM model
- retrieved sources
- toxicity input metadata
- toxicity output metadata

## Search Request Flow

The search flow is implemented in [app/api/routes/search.py](../app/api/routes/search.py).

Flow:

```text
User query
-> route determines project_id and audience
-> input guardrail
-> semantic search
-> output guardrail over retrieved text
-> return matching chunks
```

The search response returns chunk-level matches instead of an LLM-generated answer.

Each match includes:

- `doc_id`
- `full_text`
- `chunk_size`
- `source_file`
- `source_name`
- `source_url`

## Embedding Implementation

Embeddings are implemented in [app/core/embeddings.py](../app/core/embeddings.py).

The application uses Google GenAI:

```python
google.genai.Client(api_key=GEMMA_API_KEY)
```

Embedding calls use:

```python
client.models.embed_content(
    model=EMBEDDING_MODEL,
    contents=chunk,
    config={"output_dimensionality": EMBEDDING_DIM},
)
```

Current embedding model:

```text
models/gemini-embedding-2
```

Current embedding dimension:

```text
1536
```

If the embedding client is unavailable, the code falls back to local hash-based vectors. This fallback prevents crashes, but it should not be treated as production-quality semantic embedding behavior.

## Retrieval Implementation

Retrieval is implemented in [app/retrieval/semantic_search.py](../app/retrieval/semantic_search.py).

The active retrieval backend is PostgreSQL with `pgvector`.

Retrieval flow:

```text
query text
-> Gemini query embedding
-> PostgreSQL vector similarity query
-> top 20 retrieval candidates
-> optional reranker
-> final top k results
```

The SQL query searches the `knowledge_chunk_embedding` table:

```sql
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
```

The `<=>` operator performs vector distance comparison using pgvector.

## Reranking

Reranking is implemented in [app/retrieval/reranker.py](../app/retrieval/reranker.py).

Current reranker:

```text
cross-encoder/ms-marco-MiniLM-L-6-v2
```

The system first retrieves a larger candidate set from Postgres, then reranks the candidates using a cross-encoder.

Current behavior:

- retrieve `20` candidates from pgvector
- rerank against the user query
- return the final requested `k` results

This improves relevance because pgvector handles fast approximate semantic retrieval, while the reranker performs deeper query-document comparison.

## Prompt Construction

Prompt construction is implemented in [app/core/prompts.py](../app/core/prompts.py).

The prompt includes:

- project system role
- selected audience
- shared safety and grounding instructions
- project-specific rules from YAML
- recent in-memory chat history
- retrieved source chunks
- source names and source URLs

The prompt instructs the model to:

- answer only from retrieved information
- avoid inventing clinical facts
- avoid raw citations in the answer body
- use audience-appropriate language
- clearly state limitations when retrieved context is incomplete

## LLM Implementation

The LLM client is implemented in [app/core/llm.py](../app/core/llm.py).

The app uses Google GenAI for text generation.

Primary model is controlled by:

```text
GEMMA_MODEL
```

Fallback model is controlled by:

```text
GEMMA_FALLBACK
```

The code attempts the primary model first and falls back if there is a server-side failure.

## Chunking Workflow

Chunking is implemented in [scripts/chunk_markdown.py](../scripts/chunk_markdown.py).

The chunking script reads markdown files from each project's knowledge-base folder and writes chunk JSON files into `data/`.

Default chunking strategy:

```text
semantic
```

Fallback chunking strategy:

```text
recursive
```

The semantic strategy uses LangChain's `SemanticChunker` with Gemini embeddings. If semantic chunking is unavailable, the script falls back to recursive character splitting.

Typical command:

```bash
python scripts/chunk_markdown.py --project tb
```

Output files:

```text
data/<project>_<audience>_chunks.json
```

Examples:

```text
data/tb_general_chunks.json
data/tb_clinicians_chunks.json
data/cervical_cancer_general_chunks.json
data/cervical_cancer_clinicians_chunks.json
```

Each chunk includes:

- chunk text
- source file
- source name
- source URL

## Indexing Workflow

Indexing is implemented in [scripts/embed_and_index.py](../scripts/embed_and_index.py).

The indexing script:

1. Reads chunk JSON files from `data/`.
2. Generates embeddings using Gemini.
3. Connects to PostgreSQL.
4. Inserts or updates rows in `knowledge_chunk_embedding`.
5. Stores chunk text, metadata, embedding model, and vector.

Typical command:

```bash
python scripts/embed_and_index.py --project tb
```

The script uses an upsert:

```sql
ON CONFLICT (chunk_id, project_id, audience)
DO UPDATE SET ...
```

This allows re-indexing a project without manually clearing the table.

## Project Sync Workflow

Project synchronization is implemented in [scripts/sync_projects_to_db.py](../scripts/sync_projects_to_db.py).

The script reads [config/projects.yaml](../config/projects.yaml) and writes project metadata into:

- `projects`
- `project_audiences`

Typical command:

```bash
python scripts/sync_projects_to_db.py
```

This keeps PostgreSQL aware of the configured projects and audiences.

## Database Implementation

The database schema is defined in [db_schema.sql](../db_schema.sql).

Required PostgreSQL extensions:

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;
```

`pgcrypto` is used for UUID generation.

`vector` is used for pgvector embedding storage and similarity search.

## Database Table Groups

The schema can be understood in five groups:

1. project registry
2. user and admin access
3. knowledge ingestion and indexing
4. chat persistence
5. service monitoring and audit logs

## Project Registry Tables

### `projects`

Stores project-level metadata.

Important columns:

- `id`
- `name`
- `description`
- `domain_url`
- `enabled`
- `status`
- `config_json`
- `created_at`
- `updated_at`

Primary key:

```text
projects.id
```

### `project_audiences`

Stores the audiences available for each project.

Important columns:

- `id`
- `project_id`
- `audience`
- `enabled`
- `created_at`

Relationship:

```text
project_audiences.project_id -> projects.id
```

Unique constraint:

```text
UNIQUE(project_id, audience)
```

## User And Admin Tables

### `users`

Stores user accounts.

Important columns:

- `id`
- `email`
- `full_name`
- `password_hash`
- `is_active`
- `created_at`
- `updated_at`

### `roles`

Stores role definitions.

Important columns:

- `id`
- `name`
- `description`
- `created_at`

### `user_roles`

Join table between users and roles.

Relationships:

```text
user_roles.user_id -> users.id
user_roles.role_id -> roles.id
```

Unique constraint:

```text
UNIQUE(user_id, role_id)
```

### `project_memberships`

Stores project-level user memberships.

Relationships:

```text
project_memberships.project_id -> projects.id
project_memberships.user_id -> users.id
```

Unique constraint:

```text
UNIQUE(project_id, user_id, membership_role)
```

## Knowledge And Indexing Tables

### `source_assets`

Stores source documents or assets that belong to a project and audience.

Important columns:

- `id`
- `project_id`
- `audience`
- `source_name`
- `source_url`
- `source_file`
- `checksum`
- `status`
- `created_by`
- `created_at`
- `updated_at`

Relationships:

```text
source_assets.project_id -> projects.id
source_assets.created_by -> users.id
```

### `ingestion_jobs`

Tracks ingestion jobs.

Important columns:

- `id`
- `project_id`
- `audience`
- `job_type`
- `status`
- `payload`
- `error_message`
- `started_at`
- `finished_at`
- `created_at`

Relationship:

```text
ingestion_jobs.project_id -> projects.id
```

### `index_runs`

Tracks indexing runs.

Important columns:

- `id`
- `project_id`
- `audience`
- `embedding_model`
- `chunk_count`
- `status`
- `error_message`
- `started_at`
- `finished_at`
- `created_at`

Relationship:

```text
index_runs.project_id -> projects.id
```

### `knowledge_chunk_embedding`

This is the active vector search table.

Important columns:

- `id`
- `chunk_id`
- `project_id`
- `audience`
- `source_file`
- `source_name`
- `source_url`
- `chunk_text`
- `embedding_model`
- `embedding`
- `created_at`

Vector column:

```sql
embedding vector(1536) NOT NULL
```

Unique constraint:

```text
UNIQUE(chunk_id, project_id, audience)
```

Indexes:

```sql
CREATE INDEX IF NOT EXISTS idx_chunk_project_audience
ON knowledge_chunk_embedding(project_id, audience);
```

```sql
CREATE INDEX IF NOT EXISTS idx_chunk_embedding_cosine
ON knowledge_chunk_embedding
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

This table replaces the previous Chroma-based vector persistence path.

## Chat Persistence Tables

### `chat_session`

Stores chat sessions.

Important columns:

- `id`
- `project_id`
- `audience`
- `created_at`
- `last_active`

### `chat_message`

Stores both user messages and assistant messages.

Important columns:

- `id`
- `session_id`
- `project_id`
- `audience`
- `is_user`
- `message`
- `llm_prompt`
- `llm_model`
- `llm_answer`
- `sources`
- `toxicity_input`
- `toxicity_output`
- `created_at`

Relationship:

```text
chat_message.session_id -> chat_session.id
```

### `chat_feedback`

Stores feedback ratings.

Important columns:

- `id`
- `message_id`
- `project_id`
- `audience`
- `rating`
- `feedback`
- `created_at`

Relationship:

```text
chat_feedback.message_id -> chat_message.id
```

Rating constraint:

```text
rating >= 1 AND rating <= 5
```

## Monitoring And Audit Tables

### `service_health_checks`

Stores service health check records.

Important columns:

- `id`
- `project_id`
- `component`
- `status`
- `details`
- `created_at`

Relationship:

```text
service_health_checks.project_id -> projects.id
```

### `audit_logs`

Stores audit events.

Important columns:

- `id`
- `actor_user_id`
- `project_id`
- `action`
- `entity_type`
- `entity_id`
- `payload`
- `created_at`

Relationships:

```text
audit_logs.actor_user_id -> users.id
audit_logs.project_id -> projects.id
```

## Database Relationship Summary

Core project relationships:

```text
projects
-> project_audiences
-> source_assets
-> ingestion_jobs
-> index_runs
-> service_health_checks
-> audit_logs
```

User and role relationships:

```text
users
-> user_roles
-> roles
```

Project membership relationships:

```text
projects + users
-> project_memberships
```

Chat relationships:

```text
chat_session
-> chat_message
-> chat_feedback
```

Retrieval relationship:

```text
knowledge_chunk_embedding
filtered by project_id and audience
```

Important implementation detail:

Some tables store `project_id` as a logical project reference without a database-level foreign key. For example, `knowledge_chunk_embedding`, `chat_session`, `chat_message`, and `chat_feedback` store project IDs but do not currently enforce a foreign-key relationship to `projects(id)`.

## ORM Coverage

SQLAlchemy ORM models are currently defined in [app/db/models.py](../app/db/models.py).

Current ORM models:

- `ChatSession`
- `ChatMessage`
- `ChatFeedback`

The broader production schema is applied through raw SQL from [db_schema.sql](../db_schema.sql), not through SQLAlchemy ORM models.

This means:

- chat persistence uses ORM models
- project registry and vector indexing use raw SQL
- admin/indexing tables exist in the database but are not all deeply integrated into the app yet

## Current Active Architecture

The active architecture is:

```text
FastAPI
-> Gemini embeddings
-> PostgreSQL pgvector
-> cross-encoder reranker
-> Gemma/Gemini generation
-> PostgreSQL persistence
```

The old architecture used ChromaDB for vector storage. Some older documentation and utility scripts still reference Chroma, but the active retrieval path now uses PostgreSQL pgvector.

## Current Known Gaps

Important gaps to be aware of:

- Some documentation still describes the older Chroma setup.
- Some legacy scripts still use Chroma.
- `.env.example` still references an older sentence-transformer embedding model.
- The project registry is duplicated between YAML and database tables.
- Only chat tables currently have SQLAlchemy ORM models.
- Chat sessions are grouped by latest `project_id` and `audience`, not by authenticated user.
- Some logical project references are not enforced by database foreign keys.
- Schema changes are applied by startup bootstrap, not by a migration tool such as Alembic.

## Presentation Summary

In one sentence:

The current system is a project-aware medical RAG chatbot service that uses Gemini embeddings, PostgreSQL pgvector retrieval, reranking, Gemma/Gemini generation, and database-backed chat persistence.

Short technical summary:

```text
Knowledge markdown
-> semantic chunking
-> Gemini embeddings
-> PostgreSQL pgvector table
-> FastAPI search/chat routes
-> reranked retrieval
-> grounded LLM answer
-> persisted chat and feedback
```

Main improvement from the previous setup:

```text
The vector store has moved from local Chroma persistence to PostgreSQL pgvector, making the system more suitable for production deployment, centralized indexing, and multi-project retrieval.
```

