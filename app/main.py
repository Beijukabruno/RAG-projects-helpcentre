from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.admin import router as admin_router
from app.api.routes.chat import router as chat_router
from app.api.routes.feedback import router as feedback_router
from app.api.routes.health import router as health_router
from app.api.routes.search import router as search_router
from app.core.config import CORS_ALLOW_ORIGINS
from app.core.logging import configure_logging
from app.db.session import initialize_database
from app.retrieval.semantic_search import initialize_search_backends
from app.core.guardrails import initialize_guardrails
from app.core.llm import initialize_genai_client
from app.db.admin_repo import bootstrap_admin_defaults, DatabaseUnavailable


load_dotenv()
configure_logging()

OPENAPI_DESCRIPTION = (
    "Audience-aware API for chatbot answers and semantic retrieval over "
    "separate general and clinicians knowledge bases."
)

OPENAPI_TAGS = [
    {"name": "Health", "description": "Service health and readiness checks."},
    {"name": "TB", "description": "TB chatbot, semantic search, and feedback endpoints."},
    {"name": "Cervical Cancer", "description": "Cervical cancer chatbot, semantic search, and feedback endpoints."},
    {"name": "Maternal Health", "description": "Maternal health chatbot, semantic search, and feedback endpoints."},
    {"name": "Admin: Auth", "description": "Authentication and user identity endpoints."},
    {"name": "Admin: Users", "description": "User management, roles, and activation."},
    {"name": "Admin: Projects", "description": "Project lifecycle and membership management."},
    {"name": "Admin: Knowledge Base", "description": "Knowledge source ingestion, activation, and management."},
    {"name": "Admin: Logs", "description": "Operational logs and audit records."},
]

app = FastAPI(
    title="Help Centre - Chatbot Service",
    summary="Audience-aware API for chatbot answers and semantic retrieval",
    description=OPENAPI_DESCRIPTION,
    version="1.0.0",
    openapi_tags=OPENAPI_TAGS,
)

allow_origins = [origin.strip() for origin in CORS_ALLOW_ORIGINS.split(",") if origin.strip()]
if not allow_origins:
    allow_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event():
    db_ready = initialize_database()
    if db_ready:
        try:
            bootstrap_admin_defaults()
            # Refresh project registry from DB after bootstrap
            from app.core.project_manager import project_manager
            project_manager.refresh_from_db()
        except DatabaseUnavailable:
            pass
    initialize_search_backends()
    initialize_guardrails()
    initialize_genai_client()


app.include_router(health_router)
app.include_router(feedback_router)
app.include_router(chat_router)
app.include_router(search_router)
app.include_router(admin_router)
