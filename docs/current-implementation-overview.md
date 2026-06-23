# Implementation Overview: Medical Chatbot Service (RAG)

## Executive Summary
This service is an audience-aware **Retrieval-Augmented Generation (RAG)** platform designed for the Help Centre. It provides accurate, grounded medical information by combining state-of-the-art Large Language Models (LLMs) with a robust, searchable knowledge base.

### Key Capabilities
- **Audience-Awareness:** Tailored responses for `general` users and `clinicians`.
- **Multi-Project Support:** Unified API for various health domains (TB, Cervical Cancer, Maternal Health).
- **Semantic Retrieval:** High-precision search using **PostgreSQL + pgvector** and **reranking**.
- **Admin Suite:** Comprehensive management of projects, users, and medical knowledge assets.

---

## Technical Architecture

### 1. API & Backend
- **Framework:** FastAPI (Python)
- **Security:** JWT-based authentication with Role-Based Access Control (RBAC).
- **Deployment:** Dockerized with automated workflows.

### 2. Knowledge Pipeline
1. **Chunking:** Semantic or recursive splitting of Markdown/PDF sources.
2. **Embeddings:** Google Gemini (`gemini-embedding-2`) generating 1536-dim vectors.
3. **Storage:** PostgreSQL `pgvector` for scalable semantic indexing.

### 3. Retrieval & Generation
- **Semantic Search:** Vector similarity search with cosine distance.
- **Reranking:** `cross-encoder/ms-marco-MiniLM-L-6-v2` for ranking refinement.
- **Answer Generation:** Google Gemini/Gemma IT models grounded in retrieved context.
- **Guardrails:** Input/Output safety filters for medical accuracy and toxicity.

---

## Project & Audience Structure
Projects are defined in `config/projects.yaml` and synchronized to the database.

| Project | Audiences | Knowledge Source |
| :--- | :--- | :--- |
| **TB** | General, Clinicians | `knowledge_bases/tb` |
| **Cervical Cancer** | General, Clinicians | `knowledge_bases/cervical_cancer` |
| **Maternal Health**| General, Clinicians | `knowledge_bases/maternal_health` |

---

## Data Model & Persistence
The system uses PostgreSQL for all persistence needs:
- **Registry:** Project metadata, audiences, and memberships.
- **Ingestion:** Tracking source assets, ingestion jobs, and index runs.
- **Vectors:** `knowledge_chunk_embedding` table with HNSW/IVFFlat indexing.
- **Chat:** Persistence of sessions, messages, prompt history, and user feedback.

---

## Retrieval Workflow
```text
[User Query] 
     ↓
[Gemini Embedding]
     ↓
[Postgres pgvector Search] (Top 20 candidates)
     ↓
[Cross-Encoder Reranking] (Top K results)
     ↓
[Gemma/Gemini Generation] (Grounded in context)
     ↓
[Answer + Sources]
```

---

## Admin & Operations
The service includes a robust Admin API (`/admin`) for:
- **User Management:** Global and Project-level roles (Super Admin and Project Admin).
- **Project Lifecycle:** Automated onboarding flow including metadata, contact info, and audience configuration.
- **Knowledge Ingestion:** Restricted pipeline for `.md`, `.pdf`, and `.csv` metadata.
    - Automated PDF to Markdown conversion.
    - Metadata validation (CSV format, URL sanity checks).
    - Approval-gated indexing (Activation) with automated retrieval verification.
- **Audit & Monitoring:**
    - High-level platform and project-specific dashboards (Overview API).
    - Detailed Audit Logs for all sensitive actions.
    - Diagnostic tools for reviewing latest chat interactions and feedback.

