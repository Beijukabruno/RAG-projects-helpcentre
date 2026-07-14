# BRD and SRS - Help Centre Platform

## 1. Document Control
- Document type: Combined BRD and SRS (implemented-state baseline)
- Product: Help Centre multi-project chatbot and admin platform
- Scope baseline: Current implementation in this repository
- Intended audience: Product owner, engineering, QA, deployment/operations

## 2. Business Requirements (BRD)

### BR-01 Multi-project knowledge assistant
- Priority: Must
- Requirement: Platform shall support at least TB and Cervical Cancer projects with audience-aware responses.
- Business value: Enables domain-specific medical support with controlled knowledge boundaries.
- Acceptance criteria:
  - Given a project-scoped chat endpoint, when queried, then response is produced for that project and audience.
  - Given unsupported audience input, when normalized, then a safe fallback audience is used.

### BR-02 Secure admin control plane
- Priority: Must
- Requirement: Platform shall provide authenticated admin operations for users, projects, memberships, and runtime controls.
- Business value: Enables governed operations without direct database access.
- Acceptance criteria:
  - Given valid super admin credentials, when requesting protected endpoints, then operations succeed per RBAC scope.
  - Given unauthorized role, when mutation is attempted, then API returns forbidden.

### BR-03 Runtime operational toggles
- Priority: Must
- Requirement: Platform shall allow runtime feature enable/disable at project level.
- Business value: Improves reliability and performance tuning without redeploys.
- Acceptance criteria:
  - Given project feature flag update API call, when successful, then updated values are returned and applied by subsequent requests.

### BR-04 Traceability and observability
- Priority: Must
- Requirement: Platform shall provide operational views for audit logs, toxicity feed, platform/project overview, and chat history.
- Business value: Supports compliance, diagnostics, and incident response.
- Acceptance criteria:
  - Given successful admin operations, when logs are queried, then corresponding audit records exist.

### BR-05 Knowledge base lifecycle management
- Priority: Must
- Requirement: Platform shall support source upload, activation, listing, and deletion per project and audience.
- Business value: Maintains high-quality and current response grounding.
- Acceptance criteria:
  - Given KB upload request, when accepted, then ingestion job and source metadata are recorded.
  - Given activation request, when complete, then source is marked active for retrieval usage.

### BR-06 Deployment flexibility
- Priority: Should
- Requirement: Platform should run with local and deployed endpoints for admin UI.
- Business value: Enables development, QA, and production alignment.
- Acceptance criteria:
  - Given frontend in dev mode, when no explicit API URL is configured, then localhost API is used.

### BR-07 Performance and UX improvements
- Priority: Could
- Requirement: Platform could implement frontend route-level code splitting and deeper metrics dashboards.
- Business value: Better UX performance and richer operational telemetry.
- Acceptance criteria:
  - Given large frontend bundles, when code splitting is enabled, then main bundle size decreases.

## 3. System Requirements Specification (SRS)

### 3.1 Functional Requirements

#### FR-001 Authentication
- Priority: Must
- Description: System shall authenticate admin users via email/password and issue JWT bearer tokens.
- Evidence: app/core/auth.py, app/api/routes/admin.py
- Test acceptance criteria:
  - Valid credentials return access token and user context.
  - Invalid credentials return authentication error.

#### FR-002 Authorization (RBAC)
- Priority: Must
- Description: System shall enforce super admin and project admin permissions on admin endpoints.
- Evidence: app/core/auth.py, app/api/routes/admin.py
- Test acceptance criteria:
  - Super admin can perform global user/project mutations.
  - Project admin can access only scoped project operations.

#### FR-003 Project and audience chat APIs
- Priority: Must
- Description: System shall expose project and audience specific chat endpoints.
- Evidence: app/api/routes/chat.py
- Test acceptance criteria:
  - Endpoints for TB and Cervical Cancer general/clinicians return valid chat payloads.

#### FR-004 Project and audience semantic search APIs
- Priority: Must
- Description: System shall expose project and audience specific semantic search endpoints.
- Evidence: app/api/routes/search.py
- Test acceptance criteria:
  - Search returns ranked chunks with metadata for requested project and audience.

#### FR-005 Retrieval pipeline with optional reranking
- Priority: Must
- Description: System shall perform embedding-based pgvector retrieval and optional reranking.
- Evidence: app/retrieval/semantic_search.py, app/retrieval/reranker.py
- Test acceptance criteria:
  - With reranker enabled, results are reranked to requested output size.
  - With reranker disabled, top-k retrieval is returned directly.

#### FR-006 Prompt policy and response shaping
- Priority: Must
- Description: System shall apply shared prompt policy, response balance, audience guidance, and project rules.
- Evidence: app/core/prompts.py, config/projects.yaml
- Test acceptance criteria:
  - Prompt includes system role, project role, and relevant retrieved context.
  - Chat history is included only when enabled.

#### FR-007 Guardrails
- Priority: Must
- Description: System shall support toxicity checks for input and output with safe refusal.
- Evidence: app/core/guardrails.py
- Test acceptance criteria:
  - Toxic input/output yields blocked response path when enabled.
  - Guardrails disabled flag bypasses toxicity checks.

#### FR-008 Runtime feature flags
- Priority: Must
- Description: System shall resolve and apply feature flags from project config, assistant config, and env overrides.
- Evidence: app/core/project_manager.py, app/api/routes/admin.py
- Test acceptance criteria:
  - Updated project feature flags affect subsequent request behavior.
  - Env override values take precedence where configured.

#### FR-009 User management
- Priority: Must
- Description: System shall create, list, activate/deactivate, assign roles, and delete admin users.
- Evidence: app/api/routes/admin.py, app/db/admin_repo.py
- Test acceptance criteria:
  - User lifecycle endpoints perform expected mutations and enforce RBAC.

#### FR-010 Project management
- Priority: Must
- Description: System shall create, read, update, and delete projects.
- Evidence: app/api/routes/admin.py, app/db/admin_repo.py
- Test acceptance criteria:
  - Project CRUD endpoints return consistent project payloads and persist changes.

#### FR-011 Project admin membership
- Priority: Must
- Description: System shall add/remove/list project admin memberships.
- Evidence: app/api/routes/admin.py, app/db/admin_repo.py
- Test acceptance criteria:
  - Membership endpoints correctly update project access for target users.

#### FR-012 Knowledge base source lifecycle
- Priority: Must
- Description: System shall support source listing, upload, activation, and deletion per project/audience.
- Evidence: app/api/routes/admin.py, app/core/kb_admin.py
- Test acceptance criteria:
  - Upload creates source and ingestion job entries.
  - Activation updates source status for active usage.

#### FR-013 Monitoring and logs
- Priority: Must
- Description: System shall expose platform overview, project overview, audit logs, toxicity feed, and chat history endpoints.
- Evidence: app/api/routes/admin.py
- Test acceptance criteria:
  - Monitoring endpoints return structured payloads for dashboard consumption.

#### FR-014 Persistence and exports
- Priority: Should
- Description: System should persist chat and feedback, and provide CSV export endpoints.
- Evidence: app/db/persistence.py, app/api/routes/admin.py
- Test acceptance criteria:
  - CSV endpoints return expected headers and records.

#### FR-015 Frontend admin UX modules
- Priority: Must
- Description: System shall provide route-based admin dashboard pages for all operational domains.
- Evidence: interfaces/admin-dashboard/src/App.tsx, interfaces/admin-dashboard/src/pages
- Test acceptance criteria:
  - Protected routes load only after auth context resolves user session.

### 3.2 Non-Functional Requirements

#### NFR-001 Security
- Priority: Must
- Requirement: JWT-protected admin endpoints and role checks must be enforced.
- Acceptance criteria:
  - Unauthorized calls to protected admin APIs are rejected.

#### NFR-002 Availability and degradation
- Priority: Must
- Requirement: Service should expose readiness with DB/search status and degrade gracefully where designed.
- Acceptance criteria:
  - Readiness endpoint returns structured database and search status object.

#### NFR-003 Maintainability
- Priority: Should
- Requirement: Modular separation of route, core, retrieval, and data layers should be preserved.
- Acceptance criteria:
  - New features can be added by extending existing module boundaries without cross-layer coupling.

#### NFR-004 Performance
- Priority: Should
- Requirement: Retrieval and chat response path should support operational toggles for performance tuning.
- Acceptance criteria:
  - Disabling reranker reduces retrieval processing depth and execution cost.

#### NFR-005 Usability
- Priority: Should
- Requirement: Admin dashboard should present clear operational controls and monitoring views.
- Acceptance criteria:
  - Users can complete project and user management tasks without raw API console usage.

### 3.3 External Interface Requirements
- REST API interface via FastAPI routes.
- Frontend HTTP client via axios with bearer token interceptor.
- PostgreSQL and pgvector as data and vector interfaces.
- LLM and embedding providers configured via environment.

## 4. Credential and Login Requirements

### CR-01 Bootstrap super admin requirements
- Priority: Must
- Requirement: Initial super admin is created only when bootstrap credentials are set and DB is available at startup.
- Evidence: app/db/admin_repo.py (bootstrap_admin_defaults)
- Acceptance criteria:
  - With valid BOOTSTRAP_SUPER_ADMIN_EMAIL and BOOTSTRAP_SUPER_ADMIN_PASSWORD, startup creates or upgrades a super admin account.

### Current local configured values
- BOOTSTRAP_SUPER_ADMIN_EMAIL: helpcentre_admin@gmail.com
- BOOTSTRAP_SUPER_ADMIN_PASSWORD: superadminhelpcentre123

Note:
- The configured password is currently a placeholder string.
- If the account was previously created with a different password, changing env alone will not reset that existing password.

### Invalid email or password troubleshooting
1. Confirm UI points to the expected API environment (local vs deployed).
2. Confirm DB was available during startup so bootstrap logic executed.
3. Check whether user already existed in DB with an older password.
4. If needed, reset password by:
   - creating a new super admin through an existing super admin account, or
   - updating password hash directly in DB for the target user.
5. Restart API after credential/env changes to ensure bootstrap and config reloading.

## 5. MoSCoW Summary

### Must
- Auth + RBAC
- Multi-project chat/search
- Runtime feature flags
- User/project/admin membership management
- Knowledge base lifecycle operations
- Monitoring and logs
- Bootstrap admin credential path

### Should
- CSV exports and richer observability workflows
- Improved operational runbooks and formal SLOs
- Frontend performance optimizations

### Could
- Advanced dashboard analytics and incident drill-down views
- Expanded automated test coverage for ingestion and recovery paths

## 6. Verification Matrix (Sample)
- TST-AUTH-001: Login with valid super admin credentials returns JWT.
- TST-AUTH-002: Login with wrong password returns authentication error.
- TST-RBAC-001: Project admin cannot call global user mutation endpoint.
- TST-FLAG-001: Update reranker_enabled false and verify reranker bypass.
- TST-KB-001: Upload source creates ingestion job.
- TST-KB-002: Activate asset reflects in active retrieval source state.
- TST-LOG-001: Admin mutation creates audit log record.
- TST-READY-001: Readiness endpoint returns database and search status.

## 7. Referenced Implementation Files
- app/main.py
- app/api/routes/chat.py
- app/api/routes/search.py
- app/api/routes/feedback.py
- app/api/routes/admin.py
- app/core/auth.py
- app/core/prompts.py
- app/core/project_manager.py
- app/core/guardrails.py
- app/retrieval/semantic_search.py
- app/retrieval/reranker.py
- app/db/models.py
- app/db/persistence.py
- app/db/admin_repo.py
- interfaces/admin-dashboard/src/App.tsx
- interfaces/admin-dashboard/src/lib/api.ts
- config/projects.yaml
- deploy/env.production.example.txt
