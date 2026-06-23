# API Reference: Help Centre Chatbot Service

This document is the definitive reference for the Help Centre Chatbot API. It includes all public and administrative endpoints, along with the Role-Based Access Control (RBAC) definitions.

## Base URL
`http://localhost:8000`

## Authentication & RBAC
All **Admin** endpoints require a JWT Bearer Token.
Header: `Authorization: Bearer <JWT_TOKEN>`

### User Roles
| Role | Scope | Description |
| :--- | :--- | :--- |
| **Super Admin** (`super_admin`) | Platform | Full control over users, projects, audit logs, and global settings. |
| **Project Admin** (`project_admin`) | Project-Specific | Management of knowledge bases, logs, and monitoring for assigned projects. |
| **Public** | App-Level | Access to Chat, Search, and Feedback endpoints. |

---

## 1. Public Endpoints (App Integration)
These endpoints do not require authentication and are used by the chatbot frontend.

### 1.1 Chat & Search
#### POST `/{project_id}/chat/{audience}`
- **Description:** Grounded RAG chat answer.
- **Inputs:** `project_id` (path), `audience` (path: `general`|`clinicians`), `query` (body), `k` (body).
- **Response:** `{ "query": "...", "answer": "...", "sources": [...], "llm_model": "...", "toxicity_input": {...} }`

#### POST `/{project_id}/search/{audience}`
- **Description:** Semantic search retrieval (no LLM).
- **Inputs:** Same as Chat.
- **Response:** `{ "query": "...", "total_matches": 0, "matches": [...] }`

### 1.2 Feedback
#### POST `/{project_id}/feedback/rate`
- **Description:** Star rating (1-5) for the last interaction.
- **Inputs:** `project_id` (path), `rating` (body), `audience` (body), `feedback` (body, optional).

### 1.3 Service Health
- **GET `/health`**: Returns `{ "status": "ok" }`.
- **GET `/ready`**: Returns detailed database and search backend readiness.

---

## 2. Admin: Authentication
#### POST `/admin/auth/login`
- **Description:** Exchange credentials for a JWT.
- **Inputs:** `{ "email": "...", "password": "..." }`
- **Response:** `{ "access_token": "...", "token_type": "bearer", "user": { "id": "...", "roles": [...] } }`

#### GET `/admin/auth/me`
- **Description:** Validate token and get current user identity.

---

## 3. Admin: User Management
*Permissions: Super Admin only.*

- **GET `/admin/users`**: List all users.
- **POST `/admin/users`**: Create a new user account.
  - **Inputs:** `{ "email": "...", "password": "...", "full_name": "...", "role": "super_admin|project_admin", "project_ids": ["..."] }`
- **PATCH `/admin/users/{user_id}/active`**: Activate/Deactivate a user.
  - **Inputs:** `{ "is_active": true/false }`
- **DELETE `/admin/users/{user_id}`**: Permanently delete a user.
- **POST `/admin/users/{user_id}/roles`**: Assign a global role.
- **DELETE `/admin/users/{user_id}/roles/{role}`**: Revoke a global role.

---

## 4. Admin: Project Management
#### GET `/admin/projects`
- **Perms:** Super Admin.
- **Description:** List all registered projects.

#### POST `/admin/projects`
- **Perms:** Super Admin.
- **Description:** Register a new health domain.
- **Inputs:** `{ "id": "tb", "name": "Tuberculosis", "description": "...", "config_json": {} }`

#### GET `/admin/projects/{project_id}`
- **Perms:** Project Admin (assigned to this project) or Super Admin.
- **Description:** Get metadata and config for one project.

#### PATCH `/admin/projects/{project_id}`
- **Perms:** Super Admin.
- **Description:** Update project status, name, or YAML-synced configuration.

#### DELETE `/admin/projects/{project_id}`
- **Perms:** Super Admin.
- **Description:** Cascade delete project and all associated data.

#### GET/POST/DELETE `/admin/projects/{project_id}/admins`
- **Perms:** Super Admin.
- **Description:** Manage which users have `project_admin` rights to this specific project.

---

## 5. Admin: Knowledge Base (KB)
*Permissions: Project Admin (assigned) or Super Admin.*

#### GET `/admin/projects/{project_id}/knowledge-base`
- **Description:** List source assets (`.pdf`, `.md`) and their status.

#### POST `/admin/projects/{project_id}/knowledge-base`
- **Description:** Upload a source file (multipart/form-data).
- **Inputs:** `file`, `audience`, `source_name` (optional).

#### POST `/admin/projects/{project_id}/knowledge-base/{asset_id}/activate`
- **Description:** **Critical Operation.** Triggers chunking and Gemini embedding generation.

#### DELETE `/admin/projects/{project_id}/knowledge-base/{file_name}`
- **Description:** Remove a raw source file.

---

## 6. Admin: Monitoring & Diagnostics
#### GET `/admin/overview`
- **Perms:** Super Admin.
- **Description:** Global KPI dashboard (Total messages, users, projects, recent audits).

#### GET `/admin/projects/{project_id}/overview`
- **Perms:** Project Admin.
- **Description:** Project KPI dashboard (Total messages, avg rating, active ingestion jobs).

#### GET `/admin/audit-logs`
- **Perms:** Super Admin.
- **Description:** Global security audit trail.

#### GET `/admin/projects/{project_id}/audit-logs`
- **Perms:** Project Admin.
- **Description:** Security logs filtered for a specific project.

---

## 7. Admin: Raw Logs & Exports
#### GET `/admin/last-records`
- **Perms:** Super Admin.
- **Description:** List recent chat messages with LLM prompts and metadata.

#### GET `/admin/projects/{project_id}/last-records`
- **Perms:** Project Admin.
- **Description:** Chat history for one project.

#### GET `/admin/last-records-csv`
- **Perms:** Super Admin.
- **Description:** Download global message logs as CSV for analysis.

#### GET `/admin/projects/{project_id}/last-records-csv`
- **Perms:** Project Admin.
- **Description:** Download project message logs as CSV.

---

## Error Response Format
All errors return a standard detail object:
```json
{ "detail": "Specific error message explaining the failure." }
```
Common status codes: `401` (Unauth), `403` (Forbidden/Wrong Role), `404` (Not Found), `409` (Conflict), `503` (DB Unavailable).
