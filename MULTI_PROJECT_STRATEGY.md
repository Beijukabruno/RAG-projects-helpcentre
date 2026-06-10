# Multi-Project Architecture Strategy

## Vision
Transform the search-chatbot infrastructure from **TB-specific** to a **reusable, modular multi-domain platform** supporting:
- TB (current)
- Cervical Cancer
- Maternal Health Care
- Future health domains

---

## Current Bottlenecks

### Hard-Coded to TB Domain
| Component | Issue | Impact |
|-----------|-------|--------|
| **Config** | Collection names: `DSI_TB_GENERAL`, `DSI_TB_CLINICIANS` | Can't add cervical cancer without hardcoding new names |
| **Knowledge Base** | Fixed to `knowledge_bases/clinicians/`, `knowledge_bases/general/` | New projects must create new directories |
| **Database Tables** | No `project_id` field; assumes single project | Chat history mixed across projects |
| **API Routes** | `/chat/general`, `/chat/clinicians` | No way to specify which project |
| **Scripts** | `chunk_markdown.py`, `embed_and_index.py` assume TB | Must duplicate scripts for each project |
| **LLM Prompts** | Generic but all assume medical context | Can't customize instructions per domain |
| **UI Theming** | No branding system | Can't create project-specific interfaces |

---

## Proposed Architecture

### 1. Project Registry System

**File: `config/projects.yaml`**
```yaml
projects:
  tb:
    name: "Tuberculosis Knowledge Base"
    description: "TB diagnosis, treatment, guidelines"
    enabled: true
    audiences: ["general", "clinicians"]
    
    # Knowledge base configuration
    knowledge_base:
      base_path: "knowledge_bases/tb"
      sources_file: "sources.csv"
      
    # Vector DB collections
    collections:
      general: "TB_GENERAL"
      clinicians: "TB_CLINICIANS"
    
    # Database configuration
    database:
      schema_prefix: "tb_"  # Optional: use schema per project
      tenant_id: "TB"       # For tenant isolation in multi-tenant DB
    
    # LLM configuration
    llm:
      model: "gemma-3-4b-it"
      temperature: 0.7
      system_role: "You are an expert TB advisor..."
      max_history: 3
    
    # UI/Branding
    ui:
      title: "TB Help Center"
      color_primary: "#E74C3C"
      logo: "assets/tb_logo.png"

  cervical_cancer:
    name: "Cervical Cancer Knowledge Base"
    description: "Cervical cancer screening, prevention, treatment"
    enabled: false  # Not yet implemented
    audiences: ["general", "clinicians"]
    knowledge_base:
      base_path: "knowledge_bases/cervical_cancer"
      sources_file: "sources.csv"
    collections:
      general: "CERVICAL_GENERAL"
      clinicians: "CERVICAL_CLINICIANS"
    database:
      schema_prefix: "cervical_"
      tenant_id: "CERVICAL"
    llm:
      model: "gemma-3-4b-it"
      temperature: 0.7
      system_role: "You are an expert cervical cancer advisor..."
    ui:
      title: "Cervical Cancer Help Center"
      color_primary: "#9B59B6"
      logo: "assets/cervical_logo.png"

  maternal_health:
    name: "Maternal Health Knowledge Base"
    description: "Pregnancy, childbirth, postpartum care"
    enabled: false
    audiences: ["general", "clinicians", "mothers"]
    knowledge_base:
      base_path: "knowledge_bases/maternal_health"
      sources_file: "sources.csv"
    collections:
      general: "MATERNAL_GENERAL"
      clinicians: "MATERNAL_CLINICIANS"
      mothers: "MATERNAL_MOTHERS"
    database:
      schema_prefix: "maternal_"
      tenant_id: "MATERNAL"
    llm:
      model: "gemma-3-4b-it"
      temperature: 0.7
      system_role: "You are a maternal health expert..."
    ui:
      title: "Maternal Health Center"
      color_primary: "#E91E63"
      logo: "assets/maternal_logo.png"
```

---

### 2. Directory Structure

```
search-chatbot-platform/
├── knowledge_bases/
│   ├── tb/
│   │   ├── general/
│   │   │   └── md/
│   │   ├── clinicians/
│   │   │   └── md/
│   │   └── sources.csv
│   ├── cervical_cancer/
│   │   ├── general/
│   │   │   └── md/
│   │   ├── clinicians/
│   │   │   └── md/
│   │   └── sources.csv
│   └── maternal_health/
│       ├── general/
│       │   └── md/
│       ├── clinicians/
│       │   └── md/
│       ├── mothers/
│       │   └── md/
│       └── sources.csv
│
├── config/
│   ├── projects.yaml          # Project registry (NEW)
│   └── __init__.py
│
├── app/
│   ├── core/
│   │   ├── config.py          # MODIFIED: Load from projects.yaml
│   │   ├── project_manager.py # NEW: Manage projects
│   │   └── ...
│   ├── api/
│   │   └── routes/
│   │       ├── chat.py        # MODIFIED: Accept project_id
│   │       └── search.py      # MODIFIED: Accept project_id
│   ├── db/
│   │   └── models.py          # MODIFIED: Add project_id to tables
│   └── main.py                # MODIFIED: Dynamic routes per project
│
├── scripts/
│   ├── chunk_markdown.py      # MODIFIED: Add --project flag
│   ├── embed_and_index.py     # MODIFIED: Add --project flag
│   └── project_manager_cli.py # NEW: CLI for project management
│
└── interfaces/
    └── chat-ui/               # MODIFIED: Accept project parameter
```

---

### 3. Database Schema Changes

**Current (TB-only):**
```sql
CREATE TABLE chat_session (
  id UUID PRIMARY KEY,
  created_at TIMESTAMP,
  ...
);

CREATE TABLE chat_message (
  id UUID PRIMARY KEY,
  session_id UUID REFERENCES chat_session(id),
  ...
);
```

**Proposed (Multi-project):**
```sql
-- Add project_id to isolate data per project
CREATE TABLE chat_session (
  id UUID PRIMARY KEY,
  project_id VARCHAR(50) NOT NULL,  -- NEW: "tb", "cervical_cancer", "maternal_health"
  audience VARCHAR(50) NOT NULL,    -- NEW: "general", "clinicians", "mothers"
  created_at TIMESTAMP,
  ...
  FOREIGN KEY (project_id) REFERENCES projects(id)
);

CREATE TABLE chat_message (
  id UUID PRIMARY KEY,
  session_id UUID REFERENCES chat_session(id),
  project_id VARCHAR(50) NOT NULL,  -- NEW: Denormalized for query efficiency
  created_at TIMESTAMP,
  ...
);

CREATE TABLE chat_feedback (
  id UUID PRIMARY KEY,
  message_id UUID REFERENCES chat_message(id),
  project_id VARCHAR(50) NOT NULL,  -- NEW
  rating INT,
  created_at TIMESTAMP,
  ...
);

-- NEW: Projects metadata table (optional, for UI)
CREATE TABLE projects (
  id VARCHAR(50) PRIMARY KEY,
  name VARCHAR(255),
  enabled BOOLEAN,
  config_json JSONB,  -- Store full project config
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

---

### 4. Configuration Management

**File: `app/core/project_manager.py`** (NEW)
```python
from typing import Dict, List
import yaml
from pathlib import Path

class ProjectManager:
    """Centralized project configuration management"""
    
    def __init__(self, config_file: str = "config/projects.yaml"):
        self.config_file = config_file
        self.projects = self._load_projects()
    
    def _load_projects(self) -> Dict:
        """Load projects from YAML"""
        with open(self.config_file) as f:
            return yaml.safe_load(f)["projects"]
    
    def get_project(self, project_id: str) -> Dict:
        """Get project config by ID"""
        if project_id not in self.projects:
            raise ValueError(f"Project {project_id} not found")
        return self.projects[project_id]
    
    def get_active_projects(self) -> List[str]:
        """Get list of enabled projects"""
        return [pid for pid, cfg in self.projects.items() if cfg.get("enabled")]
    
    def get_audiences(self, project_id: str) -> List[str]:
        """Get audiences for a project"""
        return self.get_project(project_id)["audiences"]
    
    def get_collection_name(self, project_id: str, audience: str) -> str:
        """Get ChromaDB collection name"""
        proj = self.get_project(project_id)
        collections = proj.get("collections", {})
        if audience not in collections:
            raise ValueError(f"Audience {audience} not in project {project_id}")
        return collections[audience]
    
    def get_kb_path(self, project_id: str) -> Path:
        """Get knowledge base path for project"""
        proj = self.get_project(project_id)
        return Path(proj["knowledge_base"]["base_path"])
    
    def get_llm_config(self, project_id: str) -> Dict:
        """Get LLM settings for project"""
        return self.get_project(project_id).get("llm", {})
    
    def get_ui_config(self, project_id: str) -> Dict:
        """Get UI branding for project"""
        return self.get_project(project_id).get("ui", {})
    
    def validate_project_audience(self, project_id: str, audience: str) -> bool:
        """Check if audience is valid for project"""
        proj = self.get_project(project_id)
        return audience in proj.get("audiences", [])

# Singleton instance
project_manager = ProjectManager()
```

---

### 5. API Endpoint Structure

**New endpoint design:**

```
# Current (TB-specific)
POST /chat/general
POST /chat/clinicians
POST /api/search/general
POST /api/search/clinicians

# Proposed (Multi-project)
POST /projects/{project_id}/chat/{audience}
POST /projects/{project_id}/search/{audience}
POST /projects/{project_id}/rate
GET  /projects/{project_id}/health
GET  /projects/{project_id}/admin/last-records

# Alternatively (backward compatible):
POST /chat?project=tb&audience=general
POST /search?project=tb&audience=clinicians
```

**Example requests:**
```bash
# TB Chat
curl -X POST http://localhost:8000/projects/tb/chat/general \
  -H "Content-Type: application/json" \
  -d '{"query": "What is TB?"}'

# Cervical Cancer Chat
curl -X POST http://localhost:8000/projects/cervical_cancer/chat/clinicians \
  -H "Content-Type: application/json" \
  -d '{"query": "Screening guidelines?"}'

# Maternal Health Search (no LLM)
curl -X POST http://localhost:8000/projects/maternal_health/search/mothers \
  -H "Content-Type: application/json" \
  -d '{"query": "Postpartum care"}'
```

---

### 6. Modified Scripts

**`scripts/chunk_markdown.py`** (with project support):
```bash
# Current
python3 scripts/chunk_markdown.py

# Proposed
python3 scripts/chunk_markdown.py --project tb
python3 scripts/chunk_markdown.py --project cervical_cancer
python3 scripts/chunk_markdown.py --project maternal_health
```

**`scripts/embed_and_index.py`** (with project support):
```bash
# Proposed
python3 scripts/embed_and_index.py --project tb
python3 scripts/embed_and_index.py --project cervical_cancer --skip-reranker
```

**`scripts/project_manager_cli.py`** (NEW):
```bash
# List all projects
python3 scripts/project_manager_cli.py list

# Initialize a new project
python3 scripts/project_manager_cli.py create --name "Cervical Cancer" --id cervical_cancer

# Enable/disable project
python3 scripts/project_manager_cli.py enable cervical_cancer
python3 scripts/project_manager_cli.py disable cervical_cancer

# Chunk and index all enabled projects
python3 scripts/project_manager_cli.py build-all

# Reset/delete project data
python3 scripts/project_manager_cli.py reset cervical_cancer
```

---

### 7. Shared vs Project-Specific Components

| Component | Shared | Notes |
|-----------|--------|-------|
| **Vector DB** | Yes | Different collections per project (same ChromaDB instance) |
| **LLM API** | Yes | One Gemini API key; different prompts per project |
| **Embedding Model** | Yes | Same SentenceTransformer for all projects |
| **Reranker Model** | Yes | Same cross-encoder for all projects |
| **PostgreSQL DB** | Yes | One DB; project_id for isolation (or separate schemas) |
| **Guardrails** | Mostly | Same toxicity model, but could customize per project |
| **FastAPI Server** | Yes | One instance; routes dynamically per project |
| **Knowledge Bases** | No | Separate directories per project |
| **UI Instances** | No | Can deploy separate frontends, or shared with project parameter |

---

### 8. Implementation Phases

#### Phase 1: Foundation (Week 1-2)
- [ ] Create `config/projects.yaml` with TB + placeholders
- [ ] Implement `ProjectManager` class
- [ ] Modify `app/core/config.py` to use ProjectManager
- [ ] Add `project_id` to database models
- [ ] Update DB migrations

#### Phase 2: API Refactoring (Week 2-3)
- [ ] Modify route handlers to accept `project_id`
- [ ] Update endpoint paths: `/projects/{project_id}/chat/{audience}`
- [ ] Add input validation (project exists, audience valid)
- [ ] Test all TB endpoints with new structure

#### Phase 3: Script Refactoring (Week 3-4)
- [ ] Add `--project` flag to `chunk_markdown.py`
- [ ] Add `--project` flag to `embed_and_index.py`
- [ ] Create `project_manager_cli.py` with build-all command
- [ ] Test chunking/indexing for TB

#### Phase 4: Frontend Integration (Week 4-5)
- [ ] Update `chat-ui` to accept project parameter
- [ ] Add project selector dropdown
- [ ] Create project-specific branding (colors, logos, titles)
- [ ] Test UI with multiple projects

#### Phase 5: New Project Onboarding (Week 5-6)
- [ ] Curate cervical cancer MD sources
- [ ] Add cervical_cancer to `projects.yaml`
- [ ] Run chunking/indexing for cervical cancer
- [ ] Test full chat flow
- [ ] Repeat for maternal health

---

### 9. Data Migration Strategy

**Step 1: Add project_id column to existing tables**
```sql
-- Add NOT NULL won't work on existing data; use default first
ALTER TABLE chat_session ADD COLUMN project_id VARCHAR(50) DEFAULT 'tb';
ALTER TABLE chat_message ADD COLUMN project_id VARCHAR(50) DEFAULT 'tb';
ALTER TABLE chat_feedback ADD COLUMN project_id VARCHAR(50) DEFAULT 'tb';

-- Make it NOT NULL after backfill
ALTER TABLE chat_session ALTER COLUMN project_id SET NOT NULL;
ALTER TABLE chat_message ALTER COLUMN project_id SET NOT NULL;
ALTER TABLE chat_feedback ALTER COLUMN project_id SET NOT NULL;
```

**Step 2: No data loss** — All existing TB chat history stays as project_id='tb'

---

### 10. Benefits of This Approach

| Benefit | Impact |
|---------|--------|
| **Modularity** | Add new projects without changing core code |
| **Reusability** | Same infrastructure, different knowledge bases |
| **Isolation** | Projects don't interfere (separate collections, DB namespacing) |
| **Scalability** | Easy to add 10th, 20th health domain |
| **Maintainability** | Single codebase, multiple projects |
| **Cost Efficiency** | Shared resources (server, DB, models) |
| **Multi-tenancy Ready** | Ready for SaaS-style deployments |

---

### 11. Questions to Address During Implementation

1. **UI Deployment**: 
   - One shared UI with project selector?
   - Or separate domain-specific UIs (tb.example.com, cervical.example.com)?

2. **Database Isolation**:
   - One schema with project_id (simpler)?
   - Or separate schemas per project (better isolation)?

3. **Knowledge Base Curation**:
   - Who curates sources per project?
   - Version control for sources.csv per project?

4. **LLM Customization**:
   - Different LLM models per project (TB = Gemini, Cervical = Claude)?
   - Or same model, different prompts?

5. **Audiences**:
   - Fixed audiences: general, clinicians?
   - Or dynamic audiences per project (TB = general/clinicians, Maternal = general/clinicians/mothers)?

---

## Next Steps

1. ✅ **Branch created**: `feature/multi-project-architecture`
2. **Start with Phase 1** (implement ProjectManager)
3. **Test with TB** (ensure backward compatibility)
4. **Onboard cervical cancer** (test new project flow)
5. **Merge** once validated

---

## Rollback Plan

- Keep `main` branch untouched
- If issues arise, revert to `main` and try different architecture
- Estimated rollback time: 5 minutes

