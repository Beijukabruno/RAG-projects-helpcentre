from langchain_core.chat_history import InMemoryChatMessageHistory
from fastapi import FastAPI, HTTPException, APIRouter
from pydantic import BaseModel, Field, conint
from typing import Any, List, Optional, Dict
from sentence_transformers import SentenceTransformer
import chromadb
import os
from pathlib import Path
import google.generativeai as genai
from dotenv import load_dotenv
from transformers import pipeline
from guardrail import guard_input, guard_output
import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db_models import Base, ChatSession, ChatMessage, ChatFeedback

DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://helpcentre_user:helpcentre_pass@postgres_helpcentre:5432/helpcentre_db')
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="TB Help Centre - Chatbot Service",
    description="Chatbot API for interacting with the TB knowledge base.",
    version="1.0.0"
)

# Simple global chat history for demonstration (single user/session)
chat_history = InMemoryChatMessageHistory()

# Rating request model
class RatingRequest(BaseModel):
    rating: conint(ge=1, le=5)  # Ensures rating is between 1 and 5

# Endpoint to capture user rating
@app.post("/rate")
async def rate_service(rating_request: RatingRequest):
    db = SessionLocal()
    # Attach feedback to the latest AI message
    last_ai_msg = db.query(ChatMessage).filter_by(is_user=False).order_by(ChatMessage.created_at.desc()).first()
    feedback = ChatFeedback(message_id=last_ai_msg.id if last_ai_msg else None, rating=rating_request.rating)
    db.add(feedback)
    db.commit()
    return {"message": "Thank you for your feedback!", "rating": rating_request.rating}
# Initialize embedding model and database
BASE_DIR = Path(__file__).resolve().parent
model_name = os.environ.get('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
print(f"Loading embedding model: {model_name}")
model = SentenceTransformer(model_name)
persist_directory = str(BASE_DIR / "vector_db")
client = chromadb.PersistentClient(path=persist_directory)
collection = client.get_or_create_collection(name="DSI_TB")

# Helper functions
def search(query, k=5):
    embedding = model.encode(query)
    results = collection.query(
        query_embeddings=[embedding],
        n_results=k
    )
    return results

def call_gemma_model(prompt: str, model_name: str = 'gemma-3-4b-it') -> Dict:
    api_key = os.getenv("GEMMA_API_KEY")
    if not api_key or api_key == "your_gemma_api_key_here":
        raise ValueError("GEMMA_API_KEY environment variable is not set or is using placeholder value")

    genai.configure(api_key=api_key)

    try:
        model = genai.GenerativeModel(model_name)
    except Exception:
        try:
            model = getattr(genai, 'GenerativeModel')(model_name)
        except Exception as e:
            raise RuntimeError(f"Failed to construct Gemma model client: {e}")

    try:
        response = model.generate_content(prompt)
        model_version = model_name.split('-', 1)[-1] if '-' in model_name else "unknown"
        text = getattr(response, 'text', str(response))
        return {
            "response": text,
            "llm_model": model_name,
            "llm_model_version": model_version
        }
    except Exception as e:
        error_msg = str(e)
        if "API_KEY_INVALID" in error_msg or "API key not valid" in error_msg:
            raise ValueError(f"Invalid Gemma API key: {error_msg}")
        elif "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
            raise ValueError(f"API quota exceeded or rate limited: {error_msg}")
        else:
            raise Exception(f"Failed to generate model response: {error_msg}")

# API Models
class ChatRequest(BaseModel):
    query: str
    k: int = 5

class ChatResponse(BaseModel):
    query: str
    answer: str
    sources: List[dict]
    llm_model: str
    toxicity_input: dict
    toxicity_output: Optional[Dict] = None

class HealthResponse(BaseModel):
    status: str

class SearchRequest(BaseModel):
    query: str = Field(..., description="User query string.")
    k: int = Field(5, ge=1, le=20, description="Number of top results to return (default: 5).")

class Match(BaseModel):
    full_text: str = Field("", description="Full chunk content.")
    chunk_size: int = Field(0, description="Length of the chunk.")
    source_file: str = Field("", description="Filename where this chunk was found.")
    source_name: str = Field("", description="Human-readable source name.")
    source_url: str = Field("", description="Source URL or document link.")

class SearchResponse(BaseModel):
    query: str
    total_matches: int
    matches: List[Match]
    toxicity_input: dict
    toxicity_output: Optional[Dict] = None
    message: Optional[str] = None

# Routes
@app.post('/chat', response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    db = SessionLocal()
    # Get or create session (for now, single global session)
    session_obj = db.query(ChatSession).order_by(ChatSession.created_at.desc()).first()
    if not session_obj:
        session_obj = ChatSession()
        db.add(session_obj)
        db.commit()
        db.refresh(session_obj)

    # Guardrail on input
    proceed_in, label_in, score_in, safe_resp_in = guard_input(req.query)
    if not proceed_in:
        chat_history.add_user_message(req.query)
        chat_history.add_ai_message(safe_resp_in)
        # Store user message and AI response
        user_msg = ChatMessage(session_id=session_obj.id, is_user=True, message=req.query)
        ai_msg = ChatMessage(session_id=session_obj.id, is_user=False, message=safe_resp_in, llm_model="guardrail", toxicity_input={"label": label_in, "score": score_in})
        db.add_all([user_msg, ai_msg])
        db.commit()
        return ChatResponse(
            query=req.query,
            answer=safe_resp_in,
            sources=[],
            llm_model="guardrail",
            toxicity_input={"label": label_in, "score": score_in},
            toxicity_output=None
        )

    try:
        results = search(req.query, k=req.k)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Semantic search failed: {e}")

    # Fallback: if no chunks are retrieved, return default response
    docs = results.get('documents', [[]])[0]
    metas = results.get('metadatas', [[]])[0]
    if not docs or len(docs) == 0:
        fallback_msg = "Sorry, I could not find any relevant information for your question."
        chat_history.add_user_message(req.query)
        chat_history.add_ai_message(fallback_msg)
        # Store user message and fallback AI response
        user_msg = ChatMessage(session_id=session_obj.id, is_user=True, message=req.query)
        ai_msg = ChatMessage(session_id=session_obj.id, is_user=False, message=fallback_msg, llm_model="none", toxicity_input={"label": label_in, "score": score_in})
        db.add_all([user_msg, ai_msg])
        db.commit()
        return ChatResponse(
            query=req.query,
            answer=fallback_msg,
            sources=[],
            llm_model="none",
            toxicity_input={"label": label_in, "score": score_in},
            toxicity_output=None
        )

    # Build prompt with chat history
    prompt = build_prompt_with_history(req.query, results, chat_history)

    try:
        gen = call_gemma_model(prompt, model_name='gemma-3-4b-it')
    except Exception as e:
        # Store user message and error response
        user_msg = ChatMessage(session_id=session_obj.id, is_user=True, message=req.query, llm_prompt=prompt)
        ai_msg = ChatMessage(session_id=session_obj.id, is_user=False, message=f"LLM call failed: {e}", llm_model="gemma-3-4b-it", llm_prompt=prompt)
        db.add_all([user_msg, ai_msg])
        db.commit()
        raise HTTPException(status_code=500, detail=f"LLM call failed: {e}")

    # Guardrail on output
    proceed_out, label_out, score_out, safe_resp_out = guard_output(gen.get('response', ''))
    if not proceed_out:
        chat_history.add_user_message(req.query)
        chat_history.add_ai_message(safe_resp_out)
        # Store user message and safe AI response
        user_msg = ChatMessage(session_id=session_obj.id, is_user=True, message=req.query, llm_prompt=prompt)
        ai_msg = ChatMessage(session_id=session_obj.id, is_user=False, message=safe_resp_out, llm_model=gen.get('llm_model', 'gemma-3-4b-it'), llm_prompt=prompt, toxicity_input={"label": label_in, "score": score_in}, toxicity_output={"label": label_out, "score": score_out})
        db.add_all([user_msg, ai_msg])
        db.commit()
        return ChatResponse(
            query=req.query,
            answer=safe_resp_out,
            sources=[],
            llm_model=gen.get('llm_model', 'gemma-3-4b-it'),
            toxicity_input={"label": label_in, "score": score_in},
            toxicity_output={"label": label_out, "score": score_out}
        )

    sources = []
    for doc, meta in zip(docs, metas):
        sources.append({
            'full_text': doc,
            'chunk_size': len(doc),
            'source_file': meta.get('source_file', ''),
            'source_name': meta.get('source_name', ''),
            'source_url': meta.get('source_url', '')
        })

    # Update chat history
    chat_history.add_user_message(req.query)
    chat_history.add_ai_message(gen.get('response', ''))
    # Store user message and LLM response
    user_msg = ChatMessage(session_id=session_obj.id, is_user=True, message=req.query, llm_prompt=prompt)
    ai_msg = ChatMessage(session_id=session_obj.id, is_user=False, message=gen.get('response', ''), llm_model=gen.get('llm_model', 'gemma-3-4b-it'), llm_prompt=prompt, llm_answer=gen.get('response', ''), sources=sources, toxicity_input={"label": label_in, "score": score_in}, toxicity_output={"label": label_out, "score": score_out})
    db.add_all([user_msg, ai_msg])
    db.commit()

    return ChatResponse(
        query=req.query,
        answer=gen.get('response', ''),
        sources=sources,
        llm_model=gen.get('llm_model', 'gemma-3-4b-it'),
        toxicity_input={"label": label_in, "score": score_in},
        toxicity_output={"label": label_out, "score": score_out}
    )
def build_prompt_with_history(user_query: str, results: dict, chat_history: InMemoryChatMessageHistory, history_limit: int = 3) -> str:
    prompt = (
        "You are a TB help centre assistant. Answer the following question using ONLY the provided information. "
        "Always cite the source for each fact.\n\n"
    )
    # Add recent chat history
    history = chat_history.messages[-history_limit*2:]  # Each exchange is 2 messages
    if history:
        prompt += "Previous conversation:\n"
        for msg in history:
            role = msg.type.capitalize()
            prompt += f"{role}: {msg.content}\n"
        prompt += "\n"
    prompt += f"Question: {user_query}\n\nRelevant Information:\n"
    docs = results.get('documents', [[]])[0]
    metas = results.get('metadatas', [[]])[0]
    for i, (doc, meta) in enumerate(zip(docs, metas), 1):
        src_name = meta.get('source_name', '')
        src_url = meta.get('source_url', '')
        prompt += f"{i}. {doc}\n(Source: {src_name}, URL: {src_url})\n"
    prompt += "\nYour answer:"
    return prompt

@app.get("/health", response_model=HealthResponse, tags=["Health"])
def health() -> HealthResponse:
    return HealthResponse(status="ok")

@app.get("/ready", tags=["Health"])
def ready() -> Any:
    return {"ready": True, "mode": "chatbot"}

@app.post("/search", response_model=SearchResponse)
def semantic_search_endpoint(req: SearchRequest) -> SearchResponse:
    # Guardrail on input
    proceed_in, label_in, score_in, safe_resp_in = guard_input(req.query)
    if not proceed_in:
        return SearchResponse(
            query=req.query,
            total_matches=0,
            matches=[],
            toxicity_input={"label": label_in, "score": score_in},
            toxicity_output=None,
            message=safe_resp_in
        )

    try:
        results = search(req.query, k=req.k)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    matches = []
    for doc, meta in zip(documents, metadatas):
        match = Match(
            full_text=doc,
            chunk_size=len(doc),
            source_file=meta.get("source_file", ""),
            source_name=meta.get("source_name", ""),
            source_url=meta.get("source_url", "")
        )
        matches.append(match)

    # Guardrail on output (concatenate all docs)
    output_text = " ".join([m.full_text for m in matches])
    # --- Admin endpoint to fetch last n chat records and download as CSV ---
    from fastapi.responses import StreamingResponse
    import csv
    import io

    @app.get("/admin/last-records")
    def get_last_records(n: int = 100):
        db = SessionLocal()
        records = db.query(ChatMessage).order_by(ChatMessage.created_at.desc()).limit(n).all()
        # Return as JSON
        return [
            {
                "id": str(r.id),
                "session_id": str(r.session_id),
                "is_user": r.is_user,
                "message": r.message,
                "llm_prompt": r.llm_prompt,
                "llm_model": r.llm_model,
                "llm_answer": r.llm_answer,
                "sources": r.sources,
                "toxicity_input": r.toxicity_input,
                "toxicity_output": r.toxicity_output,
                "created_at": r.created_at.isoformat() if r.created_at else None
            }
            for r in records
        ]

    @app.get("/admin/last-records-csv")
    def get_last_records_csv(n: int = 100):
        db = SessionLocal()
        records = db.query(ChatMessage).order_by(ChatMessage.created_at.desc()).limit(n).all()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["id", "session_id", "is_user", "message", "llm_prompt", "llm_model", "llm_answer", "sources", "toxicity_input", "toxicity_output", "created_at"])
        for r in records:
            writer.writerow([
                str(r.id),
                str(r.session_id),
                r.is_user,
                r.message,
                r.llm_prompt,
                r.llm_model,
                r.llm_answer,
                r.sources,
                r.toxicity_input,
                r.toxicity_output,
                r.created_at.isoformat() if r.created_at else None
            ])
        output.seek(0)
        return StreamingResponse(output, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=last_records.csv"})
    proceed_out, label_out, score_out, safe_resp_out = guard_output(output_text)
    if not proceed_out:
        return SearchResponse(
            query=req.query,
            total_matches=0,
            matches=[],
            toxicity_input={"label": label_in, "score": score_in},
            toxicity_output={"label": label_out, "score": score_out}
        )

    return SearchResponse(
        query=req.query,
        total_matches=len(matches),
        matches=matches,
        toxicity_input={"label": label_in, "score": score_in},
        toxicity_output={"label": label_out, "score": score_out}
    )

def build_prompt(user_query: str, results: dict) -> str:
    prompt = (
        "You are a TB help centre assistant. Answer the following question using ONLY the provided information. "
        "Always cite the source for each fact.\n\n"
        f"Question: {user_query}\n\nRelevant Information:\n"
    )

    docs = results.get('documents', [[]])[0]
    metas = results.get('metadatas', [[]])[0]
    for i, (doc, meta) in enumerate(zip(docs, metas), 1):
        src_name = meta.get('source_name', '')
        src_url = meta.get('source_url', '')
        prompt += f"{i}. {doc}\n(Source: {src_name}, URL: {src_url})\n"

    prompt += "\nYour answer:"
    return prompt