# Current Release Breakdown

## Purpose

This document is the working map for the currently deployed release. The immediate goal is to understand the admin platform, the database tables behind it, and the data that is already live so the next frontend can be designed against real behavior instead of assumptions.

## Production Snapshot

The running production container and the local repository both resolve to commit `904daec` (`resolve database mismatch`). There is no local code delta against the deployed image in this workspace, so this breakdown reflects the exact production surface we can inspect here.

## Verified Live Data

From the deployed PostgreSQL container, the `projects` table currently contains:

- `tb` / `Tb` / `enabled = true` / `status = active`
- `cervical_cancer` / `Cervical Cancer` / `enabled = true` / `status = active`

The `projects` table schema in production includes:

- `id`, `name`, `description`
- `domain_url`, `domain_owner`, `contact_email`
- `enabled`, `status`, `config_json`
- `created_at`, `updated_at`

The table is referenced by the operational admin tables that matter for the UI:

- `audit_logs`
- `index_runs`
- `ingestion_jobs`
- `project_audiences`
- `project_memberships`
- `service_health_checks`
- `source_assets`

That means the admin interface should be built around project records first, then everything that hangs off a project.

## Core Code Paths

- `app/main.py`: application bootstrap, startup initialization, CORS, and router registration.
- `app/api/routes/admin.py`: auth, users, projects, project admins, knowledge-base operations, monitoring, and log exports.
- `app/core/auth.py`: login, JWT validation, and role checks.
- `app/core/project_manager.py`: project resolution from DB first, YAML fallback second.
- `app/core/kb_admin.py`: upload, ingest, activate, and remove knowledge sources.
- `app/db/admin_repo.py`: data-access layer for admin users, roles, projects, memberships, source assets, ingestion jobs, index runs, audit logs, and overview stats.
- `app/db/models.py`: ORM tables for the same admin and runtime objects.
- `app/db/session.py`: PostgreSQL initialization, schema bootstrap, compatibility migrations, and degraded-mode DB handling.
- `app/retrieval/semantic_search.py`: project-aware semantic search over the vector-backed chunk store.
- `app/schemas.py`: request and response models for public and admin endpoints.

## What The App Is Doing Now

The current production codebase is no longer a single chatbot. It is a multi-project help-centre platform with audience separation and admin controls.

- Projects currently exposed in production are `tb` and `cervical_cancer`.
- The codebase already has routing and schema support for `maternal_health`, but it is not present in the live `projects` rows shown above.
- Each project is split into `general` and `clinicians` audiences.
- Search and chat are project-scoped and audience-scoped.
- Legacy compatibility routes still exist, but the frontend should move to the project-scoped routes.

## Admin Surface In Production

### Authentication

- `POST /admin/auth/login`: username/password login with JWT issuance.
- `GET /admin/auth/me`: returns the current authenticated user context.

### Users And Roles

- `POST /admin/users`: create a user and optionally assign a role.
- `GET /admin/users`: list users with roles and project memberships.
- `PATCH /admin/users/{user_id}/active`: enable or disable a user.
- `DELETE /admin/users/{user_id}`: delete a user.
- `POST /admin/users/{user_id}/roles`: assign a global role.
- `DELETE /admin/users/{user_id}/roles/{role}`: remove a global role.

### Projects

- `GET /admin/projects`: list all projects.
- `POST /admin/projects`: create a project, audiences, and config JSON.
- `GET /admin/projects/{project_id}`: read project details.
- `PATCH /admin/projects/{project_id}`: update project metadata and status.
- `DELETE /admin/projects/{project_id}`: delete a project.
- `GET /admin/projects/{project_id}/admins`: list project admins.
- `POST /admin/projects/{project_id}/admins`: add a project admin.
- `DELETE /admin/projects/{project_id}/admins/{user_id}`: remove a project admin.

### Knowledge Base

- `GET /admin/projects/{project_id}/knowledge-base`: list disk-backed markdown sources and DB-tracked assets.
- `POST /admin/projects/{project_id}/knowledge-base`: upload a source file.
- `POST /admin/projects/{project_id}/knowledge-base/{asset_id}/activate`: activate a source and trigger indexing.
- `DELETE /admin/projects/{project_id}/knowledge-base/{file_name}`: remove a source file.

### Monitoring

- `GET /admin/overview`: platform-wide stats for super admins.
- `GET /admin/projects/{project_id}/overview`: project-level stats.
- `GET /admin/audit-logs`: global audit log view.
- `GET /admin/projects/{project_id}/audit-logs`: project audit log view.
- `GET /admin/toxicity-feed`: messages flagged as toxic.

Hidden log and export routes still exist for operational debugging:

- `GET /admin/last-records`
- `GET /admin/projects/{project_id}/last-records`
- `GET /admin/last-records-csv`
- `GET /admin/projects/{project_id}/last-records-csv`

## Database Layout

The current schema has three main groups of tables.

### Platform And Admin Tables

- `projects`: project registry and configuration.
- `project_audiences`: enabled audiences per project.
- `users`: admin and platform users.
- `roles`: global role catalog.
- `user_roles`: many-to-many mapping between users and global roles.
- `project_memberships`: project-level admin membership.
- `audit_logs`: admin action history.

### Knowledge Base And Operations Tables

- `source_assets`: uploaded and managed knowledge-base files.
- `ingestion_jobs`: source processing jobs and statuses.
- `index_runs`: vector indexing runs, chunk counts, and errors.
- `service_health_checks`: health snapshots for components.

### Runtime Conversation Tables

- `chat_session`: chat session headers.
- `chat_message`: user and assistant messages, prompts, answers, sources, and toxicity metadata.
- `chat_feedback`: star ratings and free-text feedback tied to messages.

### Retrieval Store

- `knowledge_chunk_embedding`: chunk text, source metadata, project, audience, and embeddings.

## Admin Role Model

### Super Admin

- Full platform access.
- Can manage users, roles, projects, memberships, and global monitoring.
- Can view platform-wide audit logs and exports.

### Project Admin

- Can access project-scoped endpoints for assigned projects.
- Can read project details and project-level monitoring data.
- Can manage knowledge-base files and activation for assigned projects.
- Cannot manage platform-wide users or projects unless also granted super admin.

## What The Admin UI Should Show First

The next frontend should be designed around the live database shape, not just the API list.

1. A project selector with the current projects loaded from `projects`.
2. A project overview screen that shows status, enabled audiences, memberships, recent ingestion, and recent audit activity.
3. A knowledge-base screen that shows uploaded sources, disk sources, activation state, and the most recent indexing result.
4. A monitoring screen that surfaces recent logs, toxic messages, and project health.
5. A super-admin management area for users, roles, project creation, and project administration.

## Prompting And Response Quality

The current prompt layer already has project-specific prompt rules in `config/projects.yaml`, but the guidance is still thin.

- `tb` currently uses a simple TB expert role and a few safety-oriented rules.
- `cervical_cancer` has similar minimal rules.
- `maternal_health` exists as commented scaffolding only.

That explains why some answers are overly generic or over-explain validation errors instead of giving role-appropriate help. The next improvement pass should tighten the system role, audience instructions, and answer format for each project before changing the UI.

## Practical Next Step

The best next move is to build a simulated admin UI against the existing endpoints and seed it with the real production project list and database states above. After that, we can improve the prompting templates with concrete examples from the actual poor responses.