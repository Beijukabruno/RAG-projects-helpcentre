from typing import Annotated, Dict, List, Optional

from pydantic import AliasChoices, BaseModel, Field


class ProjectScopedRatingRequest(BaseModel):
    """Request schema for project-specific feedback routes (no project_id needed; inferred from route)."""
    rating: Annotated[int, Field(ge=1, le=5)]
    audience: str = Field("general", description="Audience for the feedback entry.")
    feedback: Optional[str] = Field(None, description="Optional free-text feedback.")


class RatingRequest(BaseModel):
    """Legacy request schema; includes project_id for backward-compatible routes."""
    rating: Annotated[int, Field(ge=1, le=5)]
    project_id: str = Field("tb", description="Project id from config/projects.yaml. Use project-specific routes instead.")
    audience: str = Field("general", description="Audience for the feedback entry.")
    feedback: Optional[str] = Field(None, description="Optional free-text feedback.")


class ProjectScopedChatRequest(BaseModel):
    """Request schema for project-specific chat routes (no project_id needed; inferred from route)."""
    query: str = Field(..., validation_alias=AliasChoices("query", "question"))
    k: int = 5


class ChatRequest(BaseModel):
    """Legacy request schema; includes project_id for backward-compatible routes."""
    query: str = Field(..., validation_alias=AliasChoices("query", "question"))
    k: int = 5
    project_id: str = Field("tb", description="Project id from config/projects.yaml. Use project-specific routes instead.")


class ChatResponse(BaseModel):
    query: str
    answer: str
    sources: List[dict]
    llm_model: str
    toxicity_input: dict
    toxicity_output: Optional[Dict] = None


class HealthResponse(BaseModel):
    status: str


class ProjectScopedSearchRequest(BaseModel):
    """Request schema for project-specific routes (no project_id needed; inferred from route)."""
    query: str = Field(..., description="User query string.")
    k: int = Field(5, ge=1, le=20, description="Number of top results to return (default: 5).")


class SearchRequest(BaseModel):
    """Legacy request schema; includes project_id for backward-compatible routes."""
    query: str = Field(..., description="User query string.")
    k: int = Field(5, ge=1, le=20, description="Number of top results to return (default: 5).")
    project_id: Optional[str] = Field("tb", description="Project ID (optional, defaults to 'tb'). Use project-specific routes instead.")


class ChatResponseMatch(BaseModel):
    doc_id: str = Field("", description="Unique chunk/document ID from vector DB.")
    full_text: str = Field("", description="Full chunk content.")
    chunk_size: int = Field(0, description="Length of the chunk.")
    source_file: str = Field("", description="Filename where this chunk was found.")
    source_name: str = Field("", description="Human-readable source name.")
    source_url: str = Field("", description="Source URL or document link.")


# Alias for backward compatibility
Match = ChatResponseMatch


class SearchResponse(BaseModel):
    query: str
    total_matches: int
    matches: List[Match]
    toxicity_input: dict
    toxicity_output: Optional[Dict] = None
    message: Optional[str] = None
