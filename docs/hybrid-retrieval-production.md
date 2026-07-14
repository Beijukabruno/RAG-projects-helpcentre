# Production Hybrid Retrieval Design

## Objective
Provide reliable, audienced-correct retrieval for TB and other projects by combining semantic vector search and lexical keyword search, then fusing them with a deterministic rank strategy.

## Why This Design
The incident showed three failure classes:
1. Dense retrieval occasionally missed obvious definition/workflow chunks.
2. Audience drift could route clinicians requests to general chunks.
3. Relevance regressions could ship unnoticed without runtime checks.

This design addresses all three with architecture, governance, and validation.

## Final Architecture
1. Audience normalization (project-aware)
- Audience is normalized with `project_id` context, not static startup mappings.
- This prevents clinicians -> general fallback when project config changes in DB.

2. Vector retrieval (pgvector)
- Candidate retrieval from `knowledge_chunk_embedding` filtered by `(project_id, audience)`.
- Deterministic fallback query is used when ANN retrieval returns no rows.

3. Keyword retrieval (Postgres FTS)
- `to_tsvector` + `websearch_to_tsquery` for lexical recall.
- This captures explicit terms such as `what is tb`, `patient registration`, and product UI labels.

4. Weighted RRF fusion
- Vector and keyword rankings are fused using Reciprocal Rank Fusion.
- Weights are configurable for production tuning:
  - `HYBRID_WEIGHT_VECTOR`
  - `HYBRID_WEIGHT_KEYWORD`
- This is query-agnostic and avoids hardcoded intent branches.

5. Optional reranker
- Existing cross-encoder reranker remains downstream of hybrid retrieval.
- Feature-controlled through project feature flags.

## Runtime Configuration
Environment controls:
- `HYBRID_RETRIEVAL_ENABLED=true|false`
- `HYBRID_KEYWORD_K=30`
- `HYBRID_RRF_K=60`
- `HYBRID_WEIGHT_VECTOR=1.0`
- `HYBRID_WEIGHT_KEYWORD=1.0`

Project-level feature control (super admin):
- `hybrid_retrieval_enabled` in `llm.feature_flags`
- Managed via admin feature-flag endpoint:
  - `PATCH /admin/projects/{project_id}/feature-flags`

## Diagnostics and Observability
New diagnostics endpoint:
- `GET /ready/retrieval-diagnostics`
- Inputs: `query`, `project_id`, `audience`, `k`
- Returns:
  - top chunk ids
  - top source files
  - vector/keyword/merged candidate counts
  - effective hybrid config

Use this endpoint for rapid incident triage without invoking LLM generation.

## Canary Regression Protection
Script:
- `scripts/verify_retrieval_canaries.py`

Canaries:
1. `what is tb` (general) expects `FAQ.md` in top results.
2. `How can i register a patient` (clinicians) expects `02-nurse-user-manual.md`.
3. Audience prefix checks ensure chunk ids align with audience (`general_` vs `clinicians_`).

Exit code is non-zero on failure, suitable for CI/CD gating.

## Deployment Smoke Checks
Deployment workflow includes post-deploy retrieval smoke checks against:
- `GET /ready/retrieval-diagnostics` for TB definition query
- `GET /ready/retrieval-diagnostics` for clinicians registration workflow query

Deployment fails if expected source files are not surfaced.

## One-Time Incident Recovery Reindex
For this incident, one-time forced reindex is supported in deployment:
- Set `FORCE_REINDEX_ON_DEPLOY=1` in production `.env` (via ENV_FILE_CONTENTS secret).
- Next push triggers forced rechunk + reindex for configured projects.
- After recovery, set back to `0`.

This keeps emergency recovery explicit and auditable.

## Recommended Operating Procedure
1. Before release
- Run canary script locally.
- Validate diagnostics endpoint for target queries.

2. During deployment
- Ensure post-deploy smoke checks pass.

3. After deployment
- Monitor `top_source_files` for critical intents.
- If drift is detected, use one-time forced reindex and rerun canaries.

## Why This Is Production-Ready
- Query-agnostic fusion strategy instead of brittle intent hardcoding.
- Runtime governance via env + project feature flags.
- Built-in diagnostics for rapid incident response.
- Automated canary and deployment gating to prevent silent regressions.
- Explicit one-time recovery path for index drift incidents.
