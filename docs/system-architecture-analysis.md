# System Architecture Analysis

## Scope
This document captures the current architecture of the Help Centre platform, including backend APIs, retrieval/LLM flow, persistence, admin operations, and frontend admin dashboard integration.

## Architectural Style
- API-first modular monolith (FastAPI app with route modules and core service modules).
- Shared PostgreSQL used for:
  - app persistence (users, projects, chat logs, feedback, audit, KB metadata)
  - vector similarity search via pgvector for chunk embeddings.
- Runtime behavior controlled by project-level and assistant-level feature flags.
- React + Vite admin dashboard consuming authenticated admin APIs.

## Main Components

### 1) Client Layer
- Admin dashboard: React app in interfaces/admin-dashboard.
- Auth uses JWT bearer token in localStorage.
- Core admin pages:
  - Project Center
  - Projects
  - Project Admins
  - User Management
  - Chat History
  - System Logs

### 2) API Layer (FastAPI)
- App entrypoint: app/main.py
- Routers:
  - app/api/routes/health.py
  - app/api/routes/chat.py
  - app/api/routes/search.py
  - app/api/routes/feedback.py
  - app/api/routes/admin.py
- Multi-project domain endpoints include tb, cervical_cancer, and maternal_health.

### 3) Core Services
- project_manager: project registry and feature flag resolution.
- prompts: shared prompt strategy + optional history incorporation.
- guardrails: toxicity classification gate for input/output.
- retrieval:
  - semantic_search: pgvector retrieval
  - reranker: optional cross-encoder reranking
- auth: JWT auth and role guards.

### 4) Data Layer
- SQLAlchemy models in app/db/models.py.
- Session management in app/db/session.py.
- Persistence helpers in app/db/persistence.py.
- Admin repository in app/db/admin_repo.py.
- Schema bootstrap in db_schema.sql.

### 5) Knowledge Ingestion Layer
- Source management endpoints under /admin/projects/{project_id}/knowledge-base.
- Jobs tracked via ingestion_jobs and index_runs tables.
- Knowledge assets tracked in source_assets.

## Runtime Feature Control
Feature flags are resolved in this order:
1. project-level llm.feature_flags (highest priority)
2. assistant-level feature_flags in config/projects.yaml
3. env overrides (GUARDRAILS_ENABLED, RERANKER_ENABLED, CHAT_HISTORY_ENABLED)
4. default value passed by caller

Controlled features:
- guardrails_enabled
- reranker_enabled
- chat_history_enabled

## Information Flow

### A) Chat Request Flow
1. Client calls /{project}/chat/{audience}.
2. API normalizes audience and validates input.
3. Query embedding is generated.
4. pgvector retrieval fetches top-k chunks from knowledge_chunk_embedding.
5. Optional reranker reorders candidates.
6. Prompt builder composes instructions + context (+ history when enabled).
7. LLM generates answer.
8. Optional toxicity checks run (input/output).
9. Chat exchange persisted (if DB available).
10. Response returned with answer and source metadata.

### B) Semantic Search Flow
1. Client calls /{project}/search/{audience}.
2. Query embedding generated.
3. pgvector nearest-neighbor query executed.
4. Optional reranker applied.
5. Search response returns documents + metadata + scores/distances.

### C) Admin Operations Flow
1. Admin user logs in via /admin/auth/login.
2. JWT token attached to subsequent admin requests.
3. Role checks enforce super_admin or project_admin access.
4. Mutations write domain tables and audit logs.
5. Project config mutations refresh in-memory project cache.

### D) Knowledge Base Management Flow
1. File upload request creates a source asset + ingestion job record.
2. Background job processes source and index operations.
3. Activation endpoint promotes selected asset/version for retrieval.
4. Deletion endpoint removes source association and records audit event.

## End-to-End Flowchart
```mermaid
flowchart TD
  U[User or Admin UI] --> G{Request Type}

  G -->|Chat| C1[Chat API Route]
  G -->|Semantic Search| S1[Search API Route]
  G -->|Admin Mutation| A1[Admin API Route]
  G -->|KB Upload/Activate| K1[Knowledge Base API Route]
  G -->|Health| H1[Health API Route]

  C1 --> PM[Project Manager\nconfig + feature flags]
  C1 --> GR[Guardrails]
  C1 --> RET[Semantic Retrieval]
  RET --> VDB[(pgvector table)]
  RET --> RR[Reranker if enabled]
  C1 --> PB[Prompt Builder + optional history]
  C1 --> LLM[LLM Provider]
  C1 --> PDB[(Chat persistence tables)]
  C1 --> R1[Chat response + sources]

  S1 --> PM
  S1 --> RET
  S1 --> RR
  S1 --> R2[Search results]

  A1 --> AUTH[JWT + RBAC]
  AUTH --> DB[(Users/Projects/Roles/Memberships)]
  A1 --> AUD[(Audit logs)]
  A1 --> PM
  A1 --> R3[Admin operation response]

  K1 --> KPROC[KB service + background job]
  KPROC --> KDB[(source_assets/ingestion_jobs/index_runs)]
  KPROC --> VDB
  K1 --> AUD
  K1 --> R4[KB operation response]

  H1 --> DB
  H1 --> R5[Readiness/Health payload]
```

## Information Exchange Diagram
```mermaid
flowchart LR
  subgraph CLIENTS[Client Applications]
    CUI[Admin Dashboard]
    EUI[End-user Chat Clients]
  end

  subgraph API[FastAPI Service]
    RCHAT[Chat Routes]
    RSEARCH[Search Routes]
    RADMIN[Admin Routes]
    RHEALTH[Health Routes]
  end

  subgraph CORE[Core Logic]
    CFG[Project Manager + Flags]
    PRM[Prompt Module]
    SAF[Guardrails]
    SEM[Semantic Search]
    RER[Reranker]
    GEN[LLM Client]
  end

  subgraph STORE[Data Stores]
    APPDB[(PostgreSQL app tables)]
    VECDB[(PostgreSQL pgvector embeddings)]
  end

  CUI -- admin and monitoring requests --> RADMIN
  CUI -- health checks --> RHEALTH
  EUI -- chat requests --> RCHAT
  EUI -- search requests --> RSEARCH

  RCHAT --> CFG
  RCHAT --> SAF
  RCHAT --> SEM
  SEM --> VECDB
  SEM --> RER
  RCHAT --> PRM
  RCHAT --> GEN
  RCHAT --> APPDB

  RSEARCH --> CFG
  RSEARCH --> SEM
  RSEARCH --> RER

  RADMIN --> CFG
  RADMIN --> APPDB
  RHEALTH --> APPDB
```

## System Diagram
```mermaid
flowchart LR
  subgraph UI[Client Layer]
    A1[Admin Dashboard\nReact + Vite]
  end

  subgraph API[FastAPI Service]
    B1[Auth + RBAC\n/admin/auth, role guards]
    B2[Admin APIs\nusers, projects, KB, logs]
    B3[Chat APIs\n/project/chat/audience]
    B4[Search APIs\n/project/search/audience]
    B5[Feedback APIs\n/project/feedback/rate]
    B6[Health APIs\n/health, /ready]
  end

  subgraph CORE[Core Services]
    C1[Project Manager\nconfig + flag resolution]
    C2[Prompt Builder\nshared strategy + history]
    C3[Guardrails\nIntel/toxic-prompt-roberta]
    C4[Semantic Search\npgvector query]
    C5[Reranker\nms-marco cross-encoder]
    C6[LLM Client\nGemma/Gemini]
  end

  subgraph DATA[PostgreSQL]
    D1[(App Tables\nusers/projects/chats/feedback/audit)]
    D2[(Vector Table\nknowledge_chunk_embedding)]
    D3[(KB Tables\nsource_assets/ingestion_jobs/index_runs)]
  end

  A1 -->|Bearer JWT| B1
  A1 --> B2
  A1 --> B3
  A1 --> B4
  A1 --> B5
  A1 --> B6

  B2 --> C1
  B2 --> D1
  B2 --> D3

  B3 --> C1
  B3 --> C3
  B3 --> C4
  C4 --> D2
  B3 --> C5
  B3 --> C2
  B3 --> C6
  B3 --> D1

  B4 --> C1
  B4 --> C4
  B4 --> C5

  B5 --> D1
  B6 --> D1
```

## Full Structure Breakdown

### Repository-Level Structure
- app
  - api/routes: route controllers for health, chat, search, feedback, and admin operations.
  - core: auth, prompts, guardrails, config, project manager, llm utilities.
  - retrieval: semantic retrieval and reranking logic.
  - db: models, persistence logic, admin repository, session lifecycle.
- interfaces/admin-dashboard
  - src/pages: operational UI by admin capability.
  - src/lib/api.ts: API client base URL and docs URL wiring.
  - src/context: auth context and token lifecycle.
- config/projects.yaml
  - assistant-level prompt policy and global feature defaults.
  - project-level collections, audiences, model options, and feature flags.
- deploy
  - environment and deployment templates.
  - runtime behavior flags for guardrails/reranker/chat history.

### Data Structure (High-Level)
- Identity and access: users, roles, user_roles, project_memberships.
- Project management: projects, project_audiences.
- Retrieval assets: source_assets, ingestion_jobs, index_runs, knowledge_chunk_embedding.
- Conversation telemetry: chat_session, chat_message, chat_feedback.
- Audit and operations: audit_logs, service_health_checks.

## Flow Sequence Diagrams

### 1) Chat Request Sequence
```mermaid
sequenceDiagram
  autonumber
  participant U as User Client
  participant API as FastAPI Chat Route
  participant PM as Project Manager
  participant SR as Semantic Search
  participant DB as PostgreSQL pgvector
  participant RR as Reranker
  participant PR as Prompt Builder
  participant GR as Guardrails
  participant LLM as LLM Provider
  participant PDB as Persistence Tables

  U->>API: POST /{project}/chat/{audience}
  API->>PM: Resolve project config + feature flags
  API->>GR: Guard input (if enabled)
  API->>SR: search(query, audience, project)
  SR->>DB: Vector nearest-neighbor query
  DB-->>SR: Top candidate chunks + metadata
  alt reranker enabled
    SR->>RR: Reorder candidates
    RR-->>SR: Ranked candidates
  end
  SR-->>API: Retrieval result set
  API->>PR: Build prompt (+ history if enabled)
  API->>LLM: Generate answer
  LLM-->>API: Answer text
  API->>GR: Guard output (if enabled)
  API->>PDB: Persist chat exchange (if DB available)
  API-->>U: Chat response + sources
```

### 2) Admin Mutation Sequence
```mermaid
sequenceDiagram
  autonumber
  participant A as Admin Dashboard
  participant AUTH as Auth Route
  participant AR as Admin Route
  participant RBAC as Role Guards
  participant REPO as Admin Repository
  participant DB as PostgreSQL
  participant AUD as Audit Log
  participant PM as Project Manager Cache

  A->>AUTH: POST /admin/auth/login
  AUTH->>REPO: authenticate_user(email, password)
  REPO->>DB: Query user, roles, memberships
  DB-->>AUTH: Auth context
  AUTH-->>A: JWT access token

  A->>AR: PATCH/POST/DELETE admin mutation with Bearer token
  AR->>RBAC: Validate super_admin or project_admin scope
  RBAC-->>AR: Authorized
  AR->>REPO: Execute mutation
  REPO->>DB: Write domain data
  DB-->>REPO: Commit success
  REPO->>AUD: record_audit(action, entity, payload)
  AUD->>DB: Insert audit log row
  opt project config changed
    AR->>PM: refresh_from_db()
  end
  AR-->>A: Mutation result payload
```

### 3) Knowledge Base Ingestion Sequence
```mermaid
sequenceDiagram
  autonumber
  participant A as Admin Dashboard
  participant KB as KB Admin Route
  participant KBS as KB Service
  participant DB as PostgreSQL
  participant BG as Background Worker
  participant IDX as Indexing Pipeline
  participant VDB as pgvector Table
  participant AUD as Audit Logs

  A->>KB: POST /admin/projects/{id}/knowledge-base (file + metadata)
  KB->>KBS: add_knowledge_source(...)
  KBS->>DB: Create source_asset + ingestion_job
  DB-->>KBS: job_id + asset_id
  KBS-->>KB: Upload accepted
  KB->>BG: Queue process_ingestion_job(job_id)
  KB->>AUD: Record upload audit event
  KB-->>A: Upload response

  BG->>IDX: Load source, chunk, embed, index
  IDX->>VDB: Upsert vectors + metadata
  IDX->>DB: Update ingestion_job/index_run status
  DB-->>BG: Final status

  A->>KB: POST /admin/projects/{id}/knowledge-base/{asset_id}/activate
  KB->>KBS: activate_source(...)
  KBS->>DB: Mark active source/index metadata
  KB->>AUD: Record activation audit event
  KB-->>A: Activation result
```

## Operational Characteristics
- Startup:
  - DB initialization attempted first.
  - Admin defaults bootstrap executed when DB is ready.
  - Embedding client, reranker, and guardrails initialized.
- Degraded behavior:
  - If DB is unavailable at startup, API still serves non-persistent paths.
  - Readiness endpoint reports DB status/reason.
- Security:
  - JWT-based auth.
  - Super admin and project admin role guards on admin routes.

## Known Risks and Hardening Opportunities
- A query bug in one endpoint can affect DB availability handling if exceptions are interpreted as connection failures.
- Bundle size warning in admin frontend indicates optimization opportunity (route-level code splitting).
- Feature toggle governance can be improved with explicit audit trail views per flag change (partially implemented).

## Recommended Next Documentation
- API contract snapshot by route group and expected payload schema.
- Data model ERD with cardinality for admin/KB/chat tables.
- Deployment runbook with startup order and rollback steps.
