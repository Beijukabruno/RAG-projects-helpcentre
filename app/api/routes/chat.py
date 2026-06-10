"""Project-specific chat routes.

This module exposes hardcoded, project-level chat endpoints such as
`/tb/chat/general` and `/cervical_cancer/chat/clinicians`. Legacy
parameterized endpoints remain for backward compatibility but new
integrations should use the project-specific routes.
"""

import logging
from typing import Union

from fastapi import APIRouter, HTTPException

from app.core.chat_history import InMemoryChatMessageHistory
from app.core.config import normalize_audience
from app.core.guardrails import guard_input, guard_output
from app.core.llm import GeminiAPIError, call_gemma_model
from app.core.prompts import build_prompt_with_history
from app.core.project_manager import project_manager
from app.db.persistence import persist_chat_exchange
from app.retrieval.semantic_search import search
from app.schemas import ChatRequest, ProjectScopedChatRequest, ChatResponse


logger = logging.getLogger(__name__)
router = APIRouter()
chat_history = InMemoryChatMessageHistory()


# ============================================================================
# TB Project Routes (hardcoded)
# ============================================================================

@router.post("/tb/chat/general", response_model=ChatResponse, summary="TB - General audience", tags=["TB"])
def tb_chat_general(req: ProjectScopedChatRequest) -> ChatResponse:
    return _chat_for_audience(req=req, audience="general", project_id="tb")


@router.post("/tb/chat/clinicians", response_model=ChatResponse, summary="TB - Clinicians audience", tags=["TB"])
def tb_chat_clinicians(req: ProjectScopedChatRequest) -> ChatResponse:
    return _chat_for_audience(req=req, audience="clinicians", project_id="tb")


# ============================================================================
# Cervical Cancer Project Routes (hardcoded)
# ============================================================================

@router.post("/cervical_cancer/chat/general", response_model=ChatResponse, summary="Cervical Cancer - General audience", tags=["Cervical Cancer"])
def cervical_cancer_chat_general(req: ProjectScopedChatRequest) -> ChatResponse:
    return _chat_for_audience(req=req, audience="general", project_id="cervical_cancer")


@router.post("/cervical_cancer/chat/clinicians", response_model=ChatResponse, summary="Cervical Cancer - Clinicians audience", tags=["Cervical Cancer"])
def cervical_cancer_chat_clinicians(req: ProjectScopedChatRequest) -> ChatResponse:
    return _chat_for_audience(req=req, audience="clinicians", project_id="cervical_cancer")


# ============================================================================
# Maternal Health Project Routes (hardcoded, ready for expansion)
# ============================================================================

@router.post("/maternal_health/chat/general", response_model=ChatResponse, summary="Maternal Health - General audience", tags=["Maternal Health"])
def maternal_health_chat_general(req: ProjectScopedChatRequest) -> ChatResponse:
    return _chat_for_audience(req=req, audience="general", project_id="maternal_health")


@router.post("/maternal_health/chat/clinicians", response_model=ChatResponse, summary="Maternal Health - Clinicians audience", tags=["Maternal Health"])
def maternal_health_chat_clinicians(req: ProjectScopedChatRequest) -> ChatResponse:
    return _chat_for_audience(req=req, audience="clinicians", project_id="maternal_health")


# ============================================================================
# Legacy backward-compatible routes (optional project_id in request body)
# ============================================================================

@router.post("/chat", response_model=ChatResponse, include_in_schema=False)
def chat(req: ChatRequest) -> ChatResponse:
    """Backward-compatible generic chat endpoint; defaults to TB project."""
    project_id = req.project_id or "tb"
    return _chat_for_audience(req=req, audience="general", project_id=project_id)


@router.post("/chat/general", response_model=ChatResponse, include_in_schema=False)
def chat_general(req: ChatRequest) -> ChatResponse:
    project_id = req.project_id or "tb"
    return _chat_for_audience(req=req, audience="general", project_id=project_id)


@router.post("/chat/clinicians", response_model=ChatResponse, include_in_schema=False)
def chat_clinicians(req: ChatRequest) -> ChatResponse:
    project_id = req.project_id or "tb"
    return _chat_for_audience(req=req, audience="clinicians", project_id=project_id)


def _chat_for_audience(req: Union[ChatRequest, ProjectScopedChatRequest], audience: str, project_id: str) -> ChatResponse:
    audience = normalize_audience(audience)
    project_manager.get_project(project_id)

    proceed_in, label_in, score_in, safe_resp_in = guard_input(req.query)
    if not proceed_in:
        chat_history.add_user_message(req.query)
        chat_history.add_ai_message(safe_resp_in)
        persist_chat_exchange(
            user_message=req.query,
            ai_message=safe_resp_in,
            project_id=project_id,
            audience=audience,
            llm_model="guardrail",
            toxicity_input={"label": label_in, "score": score_in},
        )
        return ChatResponse(
            query=req.query,
            answer=safe_resp_in,
            sources=[],
            llm_model="guardrail",
            toxicity_input={"label": label_in, "score": score_in},
            toxicity_output=None,
        )

    try:
        results = search(req.query, k=req.k, audience=audience, project_id=project_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Semantic search failed: {exc}") from exc

    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    if not docs:
        fallback_msg = "Sorry, I could not find any relevant information for your question."
        chat_history.add_user_message(req.query)
        chat_history.add_ai_message(fallback_msg)
        persist_chat_exchange(
            user_message=req.query,
            ai_message=fallback_msg,
            project_id=project_id,
            audience=audience,
            llm_model="none",
            toxicity_input={"label": label_in, "score": score_in},
        )
        return ChatResponse(
            query=req.query,
            answer=fallback_msg,
            sources=[],
            llm_model="none",
            toxicity_input={"label": label_in, "score": score_in},
            toxicity_output=None,
        )

    prompt = build_prompt_with_history(project_id, audience, req.query, results, chat_history)

    try:
        # Call LLM without specifying model_name; will use GEMMA_MODEL env var or default
        gen = call_gemma_model(prompt)
    except GeminiAPIError as exc:
        persist_chat_exchange(
            user_message=req.query,
            ai_message=f"LLM provider unavailable: {exc}",
            llm_prompt=prompt,
            project_id=project_id,
            audience=audience,
            llm_model=project_id,
        )
        raise HTTPException(status_code=exc.status_code, detail=f"LLM provider unavailable: {exc}") from exc
    except Exception as exc:
        persist_chat_exchange(
            user_message=req.query,
            ai_message=f"LLM call failed: {exc}",
            llm_prompt=prompt,
            project_id=project_id,
            audience=audience,
            llm_model=project_id,
        )
        raise HTTPException(status_code=500, detail=f"LLM call failed: {exc}") from exc

    proceed_out, label_out, score_out, safe_resp_out = guard_output(gen.get("response", ""))
    if not proceed_out:
        chat_history.add_user_message(req.query)
        chat_history.add_ai_message(safe_resp_out)
        persist_chat_exchange(
            user_message=req.query,
            ai_message=safe_resp_out,
            llm_prompt=prompt,
            project_id=project_id,
            audience=audience,
            llm_model=gen.get("llm_model"),
            toxicity_input={"label": label_in, "score": score_in},
            toxicity_output={"label": label_out, "score": score_out},
        )
        return ChatResponse(
            query=req.query,
            answer=safe_resp_out,
            sources=[],
            llm_model=gen.get("llm_model"),
            toxicity_input={"label": label_in, "score": score_in},
            toxicity_output={"label": label_out, "score": score_out},
        )

    ids = results.get("ids", [[]])[0]
    sources = []
    for doc, meta, chunk_id in zip(docs, metas, ids):
        sources.append(
            {
                "doc_id": chunk_id,
                "full_text": doc,
                "chunk_size": len(doc),
                "source_file": meta.get("source_file", ""),
                "source_name": meta.get("source_name", ""),
                "source_url": meta.get("source_url", ""),
            }
        )

    answer = gen.get("response", "")
    chat_history.add_user_message(req.query)
    chat_history.add_ai_message(answer)
    persist_chat_exchange(
        user_message=req.query,
        ai_message=answer,
        llm_prompt=prompt,
        project_id=project_id,
        audience=audience,
        llm_model=gen.get("llm_model"),
        llm_answer=answer,
        sources=sources,
        toxicity_input={"label": label_in, "score": score_in},
        toxicity_output={"label": label_out, "score": score_out},
    )

    return ChatResponse(
        query=req.query,
        answer=answer,
        sources=sources,
        llm_model=gen.get("llm_model"),
        toxicity_input={"label": label_in, "score": score_in},
        toxicity_output={"label": label_out, "score": score_out},
    )
