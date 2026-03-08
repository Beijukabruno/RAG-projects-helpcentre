from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from routes.semantic_search_api import router as search_router
from typing import Any
import os

app = FastAPI(
    title="TB Help Centre - Semantic Search (no-LLM)",
    description="Semantic search API over the TB knowledge base. Returns relevant document chunks without calling an LLM.",
    version="1.0.0"
)

cors_allow_origins = os.getenv("CORS_ALLOW_ORIGINS", "*")
allow_origins = [origin.strip() for origin in cors_allow_origins.split(",") if origin.strip()]
if not allow_origins:
    allow_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class HealthResponse(BaseModel):
    status: str

@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/ready", tags=["Health"])
def ready() -> Any:
    return {"ready": True, "mode": "semantic-only"}


app.include_router(search_router)
