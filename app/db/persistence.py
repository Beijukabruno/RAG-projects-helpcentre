import datetime
import logging
import uuid

from app.db.models import ChatFeedback, ChatMessage, ChatSession
from app.db.session import db_session_context


logger = logging.getLogger(__name__)


def _get_or_create_session(db, project_id: str, audience: str, client_session_id: str):
    session_obj = (
        db.query(ChatSession)
        .filter_by(project_id=project_id, audience=audience, client_session_id=client_session_id)
        .first()
    )
    if not session_obj:
        session_obj = ChatSession(
            project_id=project_id,
            audience=audience,
            client_session_id=client_session_id,
        )
        db.add(session_obj)
        db.commit()
        db.refresh(session_obj)
    else:
        session_obj.last_active = datetime.datetime.utcnow()
        db.add(session_obj)
        db.commit()
    return session_obj


def get_recent_session_messages(
    *,
    project_id: str,
    audience: str,
    client_session_id: str,
    limit_messages: int = 6,
) -> list[dict]:
    try:
        with db_session_context() as db:
            if db is None:
                return []

            rows = (
                db.query(ChatMessage)
                .join(ChatSession, ChatMessage.session_id == ChatSession.id)
                .filter(
                    ChatMessage.project_id == project_id,
                    ChatMessage.audience == audience,
                    ChatSession.client_session_id == client_session_id,
                )
                .order_by(ChatMessage.created_at.desc())
                .limit(limit_messages)
                .all()
            )

            rows.reverse()
            return [
                {
                    "is_user": bool(row.is_user),
                    "message": row.message,
                }
                for row in rows
                if row.message
            ]
    except Exception:
        logger.exception("Failed to fetch recent session messages.")
        return []


def persist_feedback(
    rating: int,
    *,
    project_id: str = "tb",
    audience: str = "general",
    feedback_text: str | None = None,
    message_id: str | None = None,
) -> bool:
    try:
        with db_session_context() as db:
            if db is None:
                logger.warning("Skipping feedback persistence because the database is unavailable.")
                return False

            target_ai_msg = None
            if message_id:
                try:
                    msg_uuid = uuid.UUID(str(message_id))
                except ValueError:
                    logger.warning("Invalid message_id provided for feedback: %s", message_id)
                    return False

                target_ai_msg = (
                    db.query(ChatMessage)
                    .filter_by(
                        id=msg_uuid,
                        project_id=project_id,
                        audience=audience,
                        is_user=False,
                    )
                    .first()
                )
                if not target_ai_msg:
                    logger.warning(
                        "Feedback message_id not found for project=%s audience=%s message_id=%s",
                        project_id,
                        audience,
                        message_id,
                    )
                    return False
            else:
                # Backward compatibility fallback for older clients.
                target_ai_msg = (
                    db.query(ChatMessage)
                    .filter_by(project_id=project_id, audience=audience, is_user=False)
                    .order_by(ChatMessage.created_at.desc())
                    .first()
                )

            feedback = ChatFeedback(
                message_id=target_ai_msg.id if target_ai_msg else None,
                project_id=project_id,
                audience=audience,
                rating=rating,
                feedback=feedback_text,
            )
            db.add(feedback)
            db.commit()
            return True
    except Exception:
        logger.exception("Feedback persistence failed.")
        return False


def persist_chat_exchange(
    *,
    user_message: str,
    ai_message: str,
    project_id: str = "tb",
    audience: str = "general",
    llm_prompt: str | None = None,
    llm_model: str | None = None,
    llm_answer: str | None = None,
    sources: list | None = None,
    toxicity_input: dict | None = None,
    toxicity_output: dict | None = None,
    client_session_id: str | None = None,
) -> dict | None:
    try:
        with db_session_context() as db:
            if db is None:
                logger.warning("Skipping chat persistence because the database is unavailable.")
                return None

            effective_client_session_id = client_session_id or str(uuid.uuid4())
            session_obj = _get_or_create_session(
                db,
                project_id=project_id,
                audience=audience,
                client_session_id=effective_client_session_id,
            )
            user_msg = ChatMessage(
                session_id=session_obj.id,
                project_id=project_id,
                audience=audience,
                is_user=True,
                message=user_message,
                llm_prompt=llm_prompt,
            )
            ai_msg = ChatMessage(
                session_id=session_obj.id,
                project_id=project_id,
                audience=audience,
                is_user=False,
                message=ai_message,
                llm_prompt=llm_prompt,
                llm_model=llm_model,
                llm_answer=llm_answer,
                sources=sources,
                toxicity_input=toxicity_input,
                toxicity_output=toxicity_output,
            )
            db.add_all([user_msg, ai_msg])
            db.commit()
            db.refresh(user_msg)
            db.refresh(ai_msg)
            return {
                "session_id": str(session_obj.id),
                "client_session_id": effective_client_session_id,
                "user_message_id": str(user_msg.id),
                "ai_message_id": str(ai_msg.id),
            }
    except Exception:
        logger.exception("Chat persistence failed.")
        return None


def get_last_records(limit: int = 100) -> list[dict]:
    try:
        with db_session_context() as db:
            if db is None:
                logger.warning("Returning no admin records because the database is unavailable.")
                return []

            records = db.query(ChatMessage).order_by(ChatMessage.created_at.desc()).limit(limit).all()
            return [
                {
                    "id": str(record.id),
                    "session_id": str(record.session_id),
                    "project_id": record.project_id,
                    "audience": record.audience,
                    "is_user": record.is_user,
                    "message": record.message,
                    "llm_prompt": record.llm_prompt,
                    "llm_model": record.llm_model,
                    "llm_answer": record.llm_answer,
                    "sources": record.sources,
                    "toxicity_input": record.toxicity_input,
                    "toxicity_output": record.toxicity_output,
                    "created_at": record.created_at.isoformat() if record.created_at else None,
                }
                for record in records
            ]
    except Exception:
        logger.exception("Failed to fetch admin records.")
        return []


def get_last_records_for_project(project_id: str, audience: str | None = None, limit: int = 5) -> list[dict]:
    try:
        with db_session_context() as db:
            if db is None:
                logger.warning("Returning no admin records because the database is unavailable.")
                return []

            query = db.query(ChatMessage).filter(ChatMessage.project_id == project_id)
            if audience:
                query = query.filter(ChatMessage.audience == audience)
            records = query.order_by(ChatMessage.created_at.desc()).limit(limit).all()
            return [
                {
                    "id": str(record.id),
                    "session_id": str(record.session_id),
                    "project_id": record.project_id,
                    "audience": record.audience,
                    "is_user": record.is_user,
                    "message": record.message,
                    "llm_prompt": record.llm_prompt,
                    "llm_model": record.llm_model,
                    "llm_answer": record.llm_answer,
                    "sources": record.sources,
                    "toxicity_input": record.toxicity_input,
                    "toxicity_output": record.toxicity_output,
                    "created_at": record.created_at.isoformat() if record.created_at else None,
                }
                for record in records
            ]
    except Exception:
        logger.exception("Failed to fetch project admin records.")
        return []
