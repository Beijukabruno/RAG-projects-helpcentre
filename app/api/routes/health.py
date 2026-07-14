from typing import Any

from fastapi import APIRouter, Query

from app.db.session import get_database_status
from app.retrieval.semantic_search import get_search_backend_status, retrieval_diagnostics
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


@router.get("/ready/retrieval-diagnostics")
def ready_retrieval_diagnostics(
    query: str = Query(..., min_length=2),
    project_id: str = Query("tb"),
    audience: str = Query("general"),
    k: int = Query(8, ge=1, le=20),
) -> Any:
    return retrieval_diagnostics(query, project_id=project_id, audience=audience, k=k)
