from typing import Any

from fastapi import APIRouter

from app.db.session import get_database_status
from app.retrieval.semantic_search import get_search_backend_status
from app.schemas import HealthResponse


router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/ready")
def ready() -> Any:
    return {
        "ready": True,
        "mode": "chatbot",
        "database": get_database_status(),
        "search": get_search_backend_status(),
    }
