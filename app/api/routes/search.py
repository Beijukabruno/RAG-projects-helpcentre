"""Project-specific semantic search routes.

Exposes hardcoded search endpoints per project and audience, for example
`/tb/search/general` and `/cervical_cancer/search/clinicians`. Backward
compatible legacy endpoints accepting `project_id` in the request body
are kept but new clients should call the project-scoped routes.
"""

from fastapi import APIRouter, HTTPException

from app.core.config import normalize_audience
from app.core.guardrails import guard_input, guard_output
from app.core.project_manager import project_manager
from app.retrieval.semantic_search import search
from app.schemas import Match, ProjectScopedSearchRequest, SearchRequest, SearchResponse


router = APIRouter()

# TB Project Search Routes

@router.post("/tb/search/general", response_model=SearchResponse, summary="TB - Semantic search (general audience)", tags=["TB"])
def tb_search_general(req: ProjectScopedSearchRequest) -> SearchResponse:
    return _semantic_search_for_audience(req=req, audience="general", project_id="tb")


@router.post("/tb/search/clinicians", response_model=SearchResponse, summary="TB - Semantic search (clinicians audience)", tags=["TB"])
def tb_search_clinicians(req: ProjectScopedSearchRequest) -> SearchResponse:
    return _semantic_search_for_audience(req=req, audience="clinicians", project_id="tb")


# Cervical Cancer Project Search Routes 

@router.post("/cervical_cancer/search/general", response_model=SearchResponse, summary="Cervical Cancer - Semantic search (general audience)", tags=["Cervical Cancer"])
def cervical_cancer_search_general(req: ProjectScopedSearchRequest) -> SearchResponse:
    return _semantic_search_for_audience(req=req, audience="general", project_id="cervical_cancer")


@router.post("/cervical_cancer/search/clinicians", response_model=SearchResponse, summary="Cervical Cancer - Semantic search (clinicians audience)", tags=["Cervical Cancer"])
def cervical_cancer_search_clinicians(req: ProjectScopedSearchRequest) -> SearchResponse:
    return _semantic_search_for_audience(req=req, audience="clinicians", project_id="cervical_cancer")

# Maternal Health Project Search Routes 

@router.post("/maternal_health/search/general", response_model=SearchResponse, summary="Maternal Health - Semantic search (general audience)", tags=["Maternal Health"])
def maternal_health_search_general(req: ProjectScopedSearchRequest) -> SearchResponse:
    return _semantic_search_for_audience(req=req, audience="general", project_id="maternal_health")


@router.post("/maternal_health/search/clinicians", response_model=SearchResponse, summary="Maternal Health - Semantic search (clinicians audience)", tags=["Maternal Health"])
def maternal_health_search_clinicians(req: ProjectScopedSearchRequest) -> SearchResponse:
    return _semantic_search_for_audience(req=req, audience="clinicians", project_id="maternal_health")


# Legacy backward-compatible routes 

@router.post("/search", response_model=SearchResponse, include_in_schema=False)
def semantic_search_endpoint(req: SearchRequest) -> SearchResponse:
    project_id = req.project_id or "tb"
    return _semantic_search_for_audience(req=req, audience="general", project_id=project_id)


@router.post("/search/general", response_model=SearchResponse, include_in_schema=False)
def semantic_search_general(req: SearchRequest) -> SearchResponse:
    project_id = req.project_id or "tb"
    return _semantic_search_for_audience(req=req, audience="general", project_id=project_id)


@router.post("/search/clinicians", response_model=SearchResponse, include_in_schema=False)
def semantic_search_clinicians(req: SearchRequest) -> SearchResponse:
    project_id = req.project_id or "tb"
    return _semantic_search_for_audience(req=req, audience="clinicians", project_id=project_id)


@router.post("/api/search/general", response_model=SearchResponse, include_in_schema=False)
def api_semantic_search_general(req: SearchRequest) -> SearchResponse:
    project_id = req.project_id or "tb"
    return _semantic_search_for_audience(req=req, audience="general", project_id=project_id)


@router.post("/api/search/clinicians", response_model=SearchResponse, include_in_schema=False)
def api_semantic_search_clinicians(req: SearchRequest) -> SearchResponse:
    project_id = req.project_id or "tb"
    return _semantic_search_for_audience(req=req, audience="clinicians", project_id=project_id)


@router.post("/search/{audience}", response_model=SearchResponse, include_in_schema=False)
def semantic_search_by_audience(audience: str, req: SearchRequest) -> SearchResponse:
    project_id = req.project_id or "tb"
    return _semantic_search_for_audience(req=req, audience=audience, project_id=project_id)


@router.post("/api/search/{audience}", response_model=SearchResponse, include_in_schema=False)
def semantic_search_api_by_audience(audience: str, req: SearchRequest) -> SearchResponse:
    project_id = req.project_id or "tb"
    return _semantic_search_for_audience(req=req, audience=audience, project_id=project_id)


def _semantic_search_for_audience(req: SearchRequest, audience: str, project_id: str) -> SearchResponse:
    audience = normalize_audience(audience)
    project_manager.get_project(project_id)
    proceed_in, label_in, score_in, safe_resp_in = guard_input(req.query)
    if not proceed_in:
        return SearchResponse(
            query=req.query,
            total_matches=0,
            matches=[],
            toxicity_input={"label": label_in, "score": score_in},
            toxicity_output=None,
            message=safe_resp_in,
        )

    try:
        results = search(req.query, k=req.k, audience=audience, project_id=project_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Search failed: {exc}") from exc

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    ids = results.get("ids", [[]])[0]
    if not documents or not ids:
        return SearchResponse(
            query=req.query,
            total_matches=0,
            matches=[],
            toxicity_input={"label": label_in, "score": score_in},
            toxicity_output=None,
            message="No relevant chunks were found for this query.",
        )

    matches = []
    for doc, meta, chunk_id in zip(documents, metadatas, ids):
        matches.append(
            Match(
                doc_id=chunk_id,
                full_text=doc,
                chunk_size=len(doc),
                source_file=meta.get("source_file", ""),
                source_name=meta.get("source_name", ""),
                source_url=meta.get("source_url", ""),
            )
        )

    if not matches:
        return SearchResponse(
            query=req.query,
            total_matches=0,
            matches=[],
            toxicity_input={"label": label_in, "score": score_in},
            toxicity_output=None,
            message="No relevant chunks were found for this query.",
        )

    output_text = " ".join([match.full_text for match in matches])
    proceed_out, label_out, score_out, _ = guard_output(output_text)
    if not proceed_out:
        return SearchResponse(
            query=req.query,
            total_matches=0,
            matches=[],
            toxicity_input={"label": label_in, "score": score_in},
            toxicity_output={"label": label_out, "score": score_out},
        )

    return SearchResponse(
        query=req.query,
        total_matches=len(matches),
        matches=matches,
        toxicity_input={"label": label_in, "score": score_in},
        toxicity_output={"label": label_out, "score": score_out},
    )
