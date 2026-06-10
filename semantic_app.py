from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.api.routes.search import router as search_router
from app.core.logging import configure_logging


configure_logging()
app = FastAPI(
    title="TB Help Centre - Semantic Search (no-LLM)",
    description="Semantic search API over the TB knowledge base. Returns relevant document chunks without calling an LLM.",
    version="1.0.0",
)
app.include_router(health_router)
app.include_router(search_router)
