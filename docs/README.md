# Platform Requirements Baseline (Current Implementation)

This document records the currently implemented functionality in this platform, organized by project breakdown, user roles, and role-based capabilities.

Scope note:
- This baseline is derived from the active FastAPI routes and service modules in the current codebase.
- It reflects what is implemented and exposed by the API at this time.

## 1. Project Breakdown

### 1.1 Core Platform Purpose
- Multi-project RAG chatbot platform for health programs.
- Audience-aware responses and retrieval for:
  - `general`
  - `clinicians`
- Supports currently defined health domains:
  - TB
  - Cervical Cancer
  - Maternal Health

### 1.2 High-Level Components
- API layer: `app/main.py`, `app/api/routes/*`
- Auth and role checks: `app/core/auth.py`
- Project and feature-flag management: `app/core/project_manager.py`, `config/projects.yaml`
- Retrieval and reranking: `app/retrieval/semantic_search.py`, `app/retrieval/reranker.py`
- LLM orchestration and prompts: `app/core/llm.py`, `app/core/prompts.py`
- Safety guardrails: `app/core/guardrails.py`
- Database and persistence: `app/db/*`
- Knowledge-base ingestion/admin: `app/core/kb_admin.py`

### 1.3 Functional Domains
- End-user chatbot interactions (chat + semantic search)
- User feedback capture (ratings)
- Health/readiness monitoring endpoints
- Admin authentication and identity
- Admin user/role lifecycle management
- Admin project lifecycle and membership management
- Admin knowledge-base ingestion, activation, and cleanup
- Admin monitoring, audit logs, and exportable records

## 2. User Roles and Access Model

### 2.1 Role Types Implemented
- Unauthenticated Public User
  - Can access public project chat/search/feedback and health endpoints.
- Authenticated Project Admin (`project_admin`)
  - Can manage project-scoped resources for assigned project(s).
  - Super admins inherit this scope automatically.
- Authenticated Super Admin (`super_admin`)
  - Full platform-level control across users, projects, and monitoring.

### 2.2 Audience vs Role Clarification
- `general` and `clinicians` are content audiences, not auth roles.
- Auth roles are `project_admin` and `super_admin`.

## 3. Implemented Features by Role

## 3.1 Unauthenticated Public User Features

### Chat (Project-Scoped)
- `POST /tb/chat/general`
- `POST /tb/chat/clinicians`
- `POST /cervical_cancer/chat/general`
- `POST /cervical_cancer/chat/clinicians`
- `POST /maternal_health/chat/general`
- `POST /maternal_health/chat/clinicians`

Functions available:
- Ask a question and receive grounded response.
- Retrieve source-supported answers with source metadata.
- Input and output safety checks via guardrails.

### Semantic Search (Project-Scoped)
- `POST /tb/search/general`
- `POST /tb/search/clinicians`
- `POST /cervical_cancer/search/general`
- `POST /cervical_cancer/search/clinicians`
- `POST /maternal_health/search/general`
- `POST /maternal_health/search/clinicians`

Functions available:
- Query vector search per project and audience.
- Return top matches with source metadata.
- Guardrail checks on query and result content.

### Feedback (Project-Scoped)
- `POST /tb/feedback/rate`
- `POST /cervical_cancer/feedback/rate`
- `POST /maternal_health/feedback/rate`

Functions available:
- Submit rating from 1 to 5.
- Optionally submit text feedback.
- Persist feedback where DB is available.

### Health and Readiness
- `GET /health`
- `GET /ready`

Functions available:
- Basic service health check.
- Readiness payload with database and search backend status.

### Legacy Compatibility Endpoints (Still Implemented)
- Chat:
  - `POST /chat`
  - `POST /chat/general`
  - `POST /chat/clinicians`
- Search:
  - `POST /search`
  - `POST /search/general`
  - `POST /search/clinicians`
  - `POST /search/{audience}`
  - `POST /api/search/general`
  - `POST /api/search/clinicians`
  - `POST /api/search/{audience}`
- Feedback:
  - `POST /rate`

Notes:
- These are marked `include_in_schema=False` in routing, but remain implemented for backward compatibility.

## 3.2 Project Admin Features (`project_admin`)

Project admins must authenticate and be assigned to the target project.

### Authentication and Identity
- `POST /admin/auth/login`
- `GET /admin/auth/me`

### Project-Scoped Read Operations
- `GET /admin/projects/{project_id}`
- `GET /admin/projects/{project_id}/feature-flags`
- `GET /admin/projects/{project_id}/admins`

### Project-Scoped Knowledge Base Management
- `GET /admin/projects/{project_id}/knowledge-base`
- `POST /admin/projects/{project_id}/knowledge-base`
- `POST /admin/projects/{project_id}/knowledge-base/{asset_id}/activate`
- `DELETE /admin/projects/{project_id}/knowledge-base/{file_name}`

Functions available:
- List markdown sources and DB-tracked source assets.
- Upload source files (`.md`, `.pdf`, `.csv` metadata).
- Trigger/execute ingestion pipeline and source activation.
- Remove active markdown sources.

### Project-Scoped Monitoring and Logs
- `GET /admin/projects/{project_id}/overview`
- `GET /admin/projects/{project_id}/audit-logs`
- `GET /admin/projects/{project_id}/last-records` (hidden from schema)
- `GET /admin/projects/{project_id}/last-records-csv` (hidden from schema)

Functions available:
- View project metrics and activity summaries.
- View project-specific audit records.
- View/export project conversation records.

## 3.3 Super Admin Features (`super_admin`)

Super admins have all Project Admin capabilities plus platform-wide administration.

### User Lifecycle and Role Management
- `POST /admin/users`
- `GET /admin/users`
- `PATCH /admin/users/{user_id}/active`
- `DELETE /admin/users/{user_id}`
- `POST /admin/users/{user_id}/roles`
- `DELETE /admin/users/{user_id}/roles/{role}`

Functions available:
- Create users.
- Activate/deactivate users.
- Delete users.
- Assign/remove global roles.

### Project Lifecycle and Governance
- `GET /admin/projects`
- `POST /admin/projects`
- `PATCH /admin/projects/{project_id}`
- `DELETE /admin/projects/{project_id}`
- `PATCH /admin/projects/{project_id}/feature-flags`
- `POST /admin/projects/{project_id}/admins`
- `DELETE /admin/projects/{project_id}/admins/{user_id}`

Functions available:
- Create/update/delete projects.
- Configure project feature flags:
  - `guardrails_enabled`
  - `reranker_enabled`
  - `chat_history_enabled`
- Assign and remove project admins.

### Platform-Wide Monitoring and Logs
- `GET /admin/overview`
- `GET /admin/audit-logs`
- `GET /admin/toxicity-feed`
- `GET /admin/last-records` (hidden from schema)
- `GET /admin/last-records-csv` (hidden from schema)

Functions available:
- View global platform stats.
- View global audit logs.
- Review toxic-flagged messages feed.
- Export global records as JSON/CSV.

## 4. Feature Flags and Behavior Control

Implemented flags (assistant-level and project-level):
- `guardrails_enabled`
- `reranker_enabled`
- `chat_history_enabled`

Control surfaces:
- Static/default config in `config/projects.yaml`
- Runtime project updates via admin endpoint:
  - `PATCH /admin/projects/{project_id}/feature-flags`

## 5. Requirements Snapshot (Current State)

### Implemented
- Role-based access model with JWT auth.
- Public chatbot, semantic search, and feedback per project/audience.
- Project-aware admin APIs for KB, monitoring, and logs.
- Super-admin governance for users, projects, and global monitoring.
- Knowledge source upload and activation flow.
- Audit trails and data export endpoints.

### Already Provisioned for Expansion
- Maternal health routes are active for chat/search/feedback.
- Project architecture supports additional domains through project configuration and admin lifecycle endpoints.

## 6. Suggested Next Documentation Step

After validating this baseline, the next requirements document can map each implemented capability to:
- UI screens that expose it
- Data entities/tables touched
- Acceptance criteria and gaps for upcoming releases