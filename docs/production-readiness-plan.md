# Production Readiness Plan

## Purpose

This document captures the current state of the help-centre platform and the planned structure needed to move it from a project prototype into a production-ready, multi-project service.

It is intentionally split into:

- what exists today
- what is missing or incomplete
- what the production system should contain
- a phased implementation plan

## Current Platform Summary

The application is already organized as a FastAPI service with project-aware retrieval, chat, feedback, admin diagnostics, and optional database persistence.

Current main entrypoint: [app/main.py](../app/main.py)

Current supporting layers:

- API routes in [app/api/routes](../app/api/routes)
- retrieval in [app/retrieval](../app/retrieval)
- configuration and project registry in [app/core](../app/core)
- persistence in [app/db](../app/db)
- chunking and indexing scripts in [scripts](../scripts)

## What Is Already Implemented

### Embedding model

The embedding model is currently configured in [app/core/config.py](../app/core/config.py) through `EMBEDDING_MODEL`.

- default: `all-MiniLM-L6-v2`
- used by the Chroma retrieval layer in [app/retrieval/semantic_search.py](../app/retrieval/semantic_search.py)
- used by the indexing script in [scripts/embed_and_index.py](../scripts/embed_and_index.py)

### LLM

The LLM layer is implemented in [app/core/llm.py](../app/core/llm.py).

- primary model is controlled by `GEMMA_MODEL`
- fallback model is controlled by `GEMMA_FALLBACK`
- default primary model: `models/gemma-2.5-flash`
- default fallback model: `models/gemma-4-31b-it`
- the chat route builds a prompt from the query, search results, and chat history before calling the model

### Chunking

Chunking is currently handled by [scripts/chunk_markdown.py](../scripts/chunk_markdown.py).

- splitter: `RecursiveCharacterTextSplitter`
- chunk size: `1000`
- overlap: `100`
- source metadata is read from CSV files beside each knowledge base
- chunk output is written to JSON files in `data/`

### Vector database

The vector database is ChromaDB, persisted in the local `vector_db/` directory.

- client: `chromadb.PersistentClient`
- retrieval collections are project- and audience-aware
- the retrieval layer falls back to a legacy collection when the scoped collection has no matches

### Supported projects

The project registry is defined in [config/projects.yaml](../config/projects.yaml).

Currently defined projects:

- `tb`
- `cervical_cancer`
- `maternal_health`

Important note:

- the code actively wires `tb`, `cervical_cancer`, and `maternal_health` into the API routes
- the repository knowledge-base files are clearly present for `tb` and `cervical_cancer`
- `maternal_health` is defined in configuration, but it still needs a full production-grade knowledge-base and indexing review before it should be treated as complete

## Current Routes

### Health and readiness

- `GET /health`
- `GET /ready`

### Chat

Project-scoped chat routes:

- `POST /tb/chat/general`
- `POST /tb/chat/clinicians`
- `POST /cervical_cancer/chat/general`
- `POST /cervical_cancer/chat/clinicians`
- `POST /maternal_health/chat/general`
- `POST /maternal_health/chat/clinicians`

Legacy chat routes still exist for backward compatibility:

- `POST /chat`
- `POST /chat/general`
- `POST /chat/clinicians`

### Search

Project-scoped search routes:

- `POST /tb/search/general`
- `POST /tb/search/clinicians`
- `POST /cervical_cancer/search/general`
- `POST /cervical_cancer/search/clinicians`
- `POST /maternal_health/search/general`
- `POST /maternal_health/search/clinicians`

Legacy search routes still exist for backward compatibility:

- `POST /search`
- `POST /search/general`
- `POST /search/clinicians`
- `POST /api/search/general`
- `POST /api/search/clinicians`
- `POST /search/{audience}`
- `POST /api/search/{audience}`

### Feedback

- `POST /tb/feedback/rate`
- `POST /cervical_cancer/feedback/rate`
- `POST /maternal_health/feedback/rate`
- `POST /rate`

### Admin diagnostics

- `GET /admin/last-records`
- `GET /admin/projects/{project_id}/last-records`
- `GET /admin/last-records-csv`
- `GET /admin/projects/{project_id}/last-records-csv`

## Current Data and Session Model

The current persistence layer stores chat and feedback history in SQLAlchemy models defined in [app/db/models.py](../app/db/models.py).

Current tables:

- `chat_session`
- `chat_message`
- `chat_feedback`

Current persistence behavior:

- session records are grouped by `project_id` and `audience`
- chat messages store the prompt, answer, sources, and toxicity labels
- feedback is attached to the latest assistant message for a project and audience
- the database is optional at runtime; the API continues to run if Postgres is unavailable

## What Needs Production Restructuring

### 1. User and role hierarchy

The platform uses **two consolidated roles**. The previously proposed
`content manager`, `reviewer/approver`, and `read-only analyst` roles are
folded into these two — their responsibilities become permissions granted to
project admins (or kept by super admins), rather than separate roles. This
keeps the access model simple while still covering every responsibility.

Two roles:

- **super admin** — platform-wide authority across all projects
- **project admin** — authority scoped to the project(s) they are a member of

#### Role definitions

**super admin** (global; not tied to any single project):

- onboard, approve, pause, disable, and retire projects
- view chat/feedback/diagnostics across **all** projects
- manage system-wide settings and model defaults
- manage database and vector-index integrity
- create users and assign project admins
- absorbs the old "read-only analyst" capability globally (sees everything)

**project admin** (scoped to assigned projects via `project_memberships`):

- manage the assigned project's knowledge base (the old "content manager" role)
- upload or remove source materials and validate source metadata
- trigger and review chunking / indexing runs (the old "reviewer/approver" role)
- review indexing and retrieval status for their project
- view chat/feedback/diagnostics for their project only
- manage their project's audience enable/disable states

#### Permission matrix

| Capability | super admin | project admin |
|---|---|---|
| View diagnostics / chat records — all projects | ✅ | ❌ |
| View diagnostics / chat records — own project | ✅ | ✅ (own only) |
| Onboard / retire projects | ✅ | ❌ |
| Enable/disable a project | ✅ | ❌ |
| Enable/disable an audience within a project | ✅ | ✅ (own only) |
| Upload / remove source assets | ✅ | ✅ (own only) |
| Trigger chunking / indexing | ✅ | ✅ (own only) |
| Manage users & assign project admins | ✅ | ❌ |
| Manage system-wide model/settings defaults | ✅ | ❌ |

Enforcement maps onto the existing schema: a user's global role lives in
`user_roles` (role `super_admin`), and project scoping lives in
`project_memberships` (`membership_role = 'project_admin'`).

### 2. Project onboarding flow

Every new project should have a structured onboarding path.

Required onboarding inputs:

- project title
- project identifier
- project description
- target audiences
- domain owner/contact
- source knowledge base files
- source CSV metadata
- optional public link/domain
- routing/branding settings
- enablement status

Required uploaded content:

- PDFs and/or markdown source files
- source metadata CSV
- optionally web links or document URLs

Required processing steps:

- convert PDFs to markdown
- validate source names and links
- chunk the markdown files
- generate embeddings
- write vectors into the correct project collections
- verify retrieval and basic answer quality

### 3. Database redesign for production

The current DB schema should evolve into a production-ready Postgres setup with two layers of storage:

Operational tables:

- projects
- project_audiences
- project_status
- users
- roles
- user_roles
- project_memberships
- ingestion_jobs
- source_assets
- source_asset_versions
- index_runs
- service_health_checks
- audit_logs

Conversation tables:

- chat_session
- chat_message
- chat_feedback

Vector storage should remain separate from relational admin data, but still be tightly linked through project IDs, audience IDs, and source IDs.

### 4. Project activation and shutdown

Admins should be able to:

- activate a project
- pause a project
- disable a project
- retire a project
- inspect whether its API endpoints and retrieval collections are healthy

This should be reflected in both the project registry and the database state, not only in static YAML.

### 5. Session and logging restructuring

Current chat session handling is minimal and needs to be formalized for production.

Needed improvements:

- stronger session identity
- user identity or anonymous session identity
- request correlation IDs
- ingestion job tracking
- index build tracking
- admin audit trail
- retention policies

## Knowledge Base Strategy

The current system already supports project-specific knowledge bases with audience separation.

Current pattern:

- `knowledge_bases/<project>/<audience>/md`
- `knowledge_bases/<project>/<audience>/sources.csv`

For production, each project should have a clear onboarding contract.

Suggested knowledge-base requirements:

- source PDFs or markdown documents
- matching metadata CSV
- source title
- source URL or reference link
- document owner
- version or revision date
- audience mapping
- approval status

Suggested validation rules:

- every uploaded source must have traceable metadata
- every collection must be tied to a project and audience
- indexing must not proceed if required metadata is missing
- project content must be reviewable before activation

## Production Target Architecture

### Control plane

The admin system should manage:

- projects
- users and roles
- audience policies
- onboarding jobs
- indexing jobs
- health and service status
- enable/disable controls

### Data plane

The runtime help-centre should serve:

- project-scoped chat
- project-scoped semantic search
- feedback capture
- retrieval from the correct vector collection
- model selection per project

### Storage plane

Recommended long-term split:

- Postgres for metadata, users, sessions, audit, and admin state
- Chroma or another vector store for embeddings
- object storage for uploaded PDFs, markdown, and generated artifacts

## Phased Implementation Plan

This plan is sequenced so each phase ships something usable and de-risks the
next. RBAC and the database redesign are deliberately interleaved because the
admin endpoints are meaningless without authorization, and authorization needs
the user/role/membership tables to be real (not just empty scaffolding).

### Current baseline (as of this revision)

- All operational tables already exist in `db_schema.sql` but `users`, `roles`,
  `user_roles`, `project_memberships`, `audit_logs`, `source_assets`,
  `ingestion_jobs`, `index_runs`, and `service_health_checks` are **empty and
  unused**.
- The four admin diagnostics routes exist but are **unauthenticated** and read
  only `chat_message`:
  - `GET /admin/last-records`
  - `GET /admin/projects/{project_id}/last-records`
  - `GET /admin/last-records-csv`
  - `GET /admin/projects/{project_id}/last-records-csv`
- `scripts/inspect_db.py` can be used at any time to print the live DB shape.

### Phase 1 — Auth + RBAC foundation (DB redesign slice 1)

Goal: real users, two roles, and enforced authorization on the existing admin
routes.

1. Schema additions to `db_schema.sql`:
   - seed roles `super_admin` and `project_admin` (idempotent `INSERT`).
   - add `project_audiences.enabled` usage and a `projects.status` lifecycle
     check (`active | paused | disabled | retired`).
   - add indexes on `user_roles(user_id)` and `project_memberships(user_id)`.
2. ORM models for `User`, `Role`, `UserRole`, `ProjectMembership` in
   `app/db/models.py` (currently only chat tables have ORM models).
3. Auth layer in `app/core/auth.py`:
   - password hashing (passlib/bcrypt) and JWT issuance (`/auth/login`).
   - `get_current_user`, `require_super_admin`, and
     `require_project_access(project_id)` FastAPI dependencies.
4. Protect the admin routes:
   - global routes (`/admin/last-records*`) → `require_super_admin`.
   - project routes (`/admin/projects/{project_id}/last-records*`) →
     `require_project_access` (super admin OR project admin of that project).
5. Seed script `scripts/create_admin_user.py` to bootstrap the first super admin.
6. Write every admin/auth action to `audit_logs`.

### Phase 2 — Project lifecycle & membership management

Goal: super admins manage projects and assign project admins from the DB, not
from static YAML alone.

1. `POST/PATCH /admin/projects` — create/update project metadata + status.
2. `POST /admin/projects/{project_id}/members` — assign/remove project admins.
3. `POST /admin/projects/{project_id}/status` — activate / pause / disable / retire.
4. Make the chat/search routes respect `projects.status` and
   `project_audiences.enabled` (reject disabled projects/audiences).
5. Migrate the YAML registry to be DB-backed at runtime (YAML becomes the seed
   source; DB becomes the source of truth), reconciled by
   `scripts/sync_projects_to_db.py`.

### Phase 3 — Source management & onboarding pipeline

Goal: a structured path from "new project" to "indexed and queryable", driven
by project admins and tracked in the DB. See the dedicated onboarding section
below; each step writes to `source_assets`, `ingestion_jobs`, and `index_runs`.

1. `POST /admin/projects/{project_id}/sources` — upload source file + metadata
   (writes `source_assets`, stores file in object storage / local data dir).
2. PDF→markdown conversion job (reuse `scripts/convert.sh` / existing tooling),
   tracked as an `ingestion_job`.
3. Chunking + embedding triggered as an `index_run` (wraps
   `scripts/chunk_markdown.py` + `scripts/embed_and_index.py`).
4. Validation gate: a project cannot be `active` until at least one successful
   `index_run` exists for each enabled audience.

### Phase 4 — Runtime hardening

1. Populate `service_health_checks` from the `/ready` probe (DB, vector store,
   embedding client, reranker).
2. Add request correlation IDs and per-request audit context.
3. Formalize session identity (currently sessions are grouped by latest
   `project_id`/`audience`, not by user or client).
4. Retention policy job for chat/audit data.

### Phase 5 — Admin UI and operations

1. Super admin dashboard (projects, users, health, cross-project analytics).
2. Project admin pages (own project's sources, index status, chat/feedback).
3. Surface project enable/disable + indexing status in the UI.

### Suggested starting point

Phase 1 is the smallest self-contained slice that delivers real value: it turns
the empty `users`/`roles`/`project_memberships` tables into an enforced
two-role access model and secures the four existing admin endpoints.

## Immediate Next Step

Before any implementation work starts, the next artifact should be a more detailed specification for:

1. the admin and project-admin permission matrix
2. the onboarding form and required source fields
3. the production database schema
4. the migration path from the current YAML-backed project registry to a persistent Postgres-backed registry

## Implementation Status Update

The first production migration slice has been started in code:

- embeddings default switched to Gemini embedding model in [app/core/config.py](../app/core/config.py)
- shared Gemini embeddings client added in [app/core/embeddings.py](../app/core/embeddings.py)
- retrieval switched from Chroma persistence to PostgreSQL pgvector query in [app/retrieval/semantic_search.py](../app/retrieval/semantic_search.py)
- chunking script now supports semantic chunking strategy in [scripts/chunk_markdown.py](../scripts/chunk_markdown.py)
- indexing script now writes embeddings into Postgres vector table in [scripts/embed_and_index.py](../scripts/embed_and_index.py)
- production schema expanded with project/admin/indexing/vector tables in [db_schema.sql](../db_schema.sql)
- DB startup bootstrap now applies schema and required extensions in [app/db/session.py](../app/db/session.py)
- project registry sync script added in [scripts/sync_projects_to_db.py](../scripts/sync_projects_to_db.py)
- deployment stack moved to pgvector-enabled Postgres image in [deploy/docker/docker-compose.yml](../deploy/docker/docker-compose.yml)
