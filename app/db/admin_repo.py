"""Data-access helpers for admin: users, roles, projects, memberships, audit.

All functions use the shared `db_session_context`. They raise RuntimeError when
the database is unavailable so callers can surface a clear 503, rather than
silently returning empty data (admin operations must not pretend to succeed).
"""

import datetime
import logging
import uuid as uuid_lib

from app.core.config import (
    BOOTSTRAP_SUPER_ADMIN_EMAIL,
    BOOTSTRAP_SUPER_ADMIN_PASSWORD,
    ROLE_PROJECT_ADMIN,
    ROLE_SUPER_ADMIN,
)
from app.db.models import (
    Project,
    ProjectAudience,
    ProjectMembership,
    Role,
    User,
    UserRole,
)
from app.db.session import db_session_context


logger = logging.getLogger(__name__)


class DatabaseUnavailable(RuntimeError):
    """Raised when an admin operation needs the DB but it is unavailable."""


def _require(db):
    if db is None:
        raise DatabaseUnavailable("Database is unavailable.")
    return db


# --------------------------------------------------------------------------- #
# Serialization helpers
# --------------------------------------------------------------------------- #

def _user_dict(user: User, roles=None, project_ids=None) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "roles": roles if roles is not None else [],
        "project_ids": project_ids if project_ids is not None else [],
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


def _project_dict(p: Project) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "description": p.description,
        "domain_url": p.domain_url,
        "domain_owner": p.domain_owner,
        "contact_email": p.contact_email,
        "enabled": p.enabled,
        "status": p.status,
        "config_json": p.config_json,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        "audiences": [a.audience for a in p.audiences] if hasattr(p, "audiences") else [],
    }


# --------------------------------------------------------------------------- #
# Users + auth reads
# --------------------------------------------------------------------------- #

def get_user_by_email(email: str) -> User | None:
    with db_session_context() as db:
        _require(db)
        return db.query(User).filter(User.email == email.lower().strip()).first()


def get_user_auth_context(user_id) -> dict | None:
    """Return id/email/active/roles/project_ids for a user, or None if missing."""
    with db_session_context() as db:
        _require(db)
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        role_names = [
            r.name
            for r in db.query(Role)
            .join(UserRole, UserRole.role_id == Role.id)
            .filter(UserRole.user_id == user.id)
            .all()
        ]
        project_ids = [
            m.project_id
            for m in db.query(ProjectMembership)
            .filter(
                ProjectMembership.user_id == user.id,
                ProjectMembership.membership_role == ROLE_PROJECT_ADMIN,
            )
            .all()
        ]
        return _user_dict(user, roles=role_names, project_ids=project_ids)


def create_user(*, email: str, full_name: str | None, password_hash: str) -> dict:
    with db_session_context() as db:
        _require(db)
        email = email.lower().strip()
        if db.query(User).filter(User.email == email).first():
            raise ValueError(f"User with email {email} already exists.")
        user = User(email=email, full_name=full_name, password_hash=password_hash)
        db.add(user)
        db.commit()
        db.refresh(user)
        return _user_dict(user)


def list_users() -> list[dict]:
    with db_session_context() as db:
        _require(db)
        users = db.query(User).order_by(User.created_at.desc()).all()
        out = []
        for u in users:
            ctx = get_user_auth_context(u.id)
            out.append(ctx if ctx else _user_dict(u))
        return out


def set_user_active(user_id, active: bool) -> bool:
    with db_session_context() as db:
        _require(db)
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        user.is_active = active
        user.updated_at = datetime.datetime.utcnow()
        db.commit()
        return True


def delete_user(user_id) -> bool:
    with db_session_context() as db:
        _require(db)
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        db.delete(user)
        db.commit()
        return True


# --------------------------------------------------------------------------- #
# Roles
# --------------------------------------------------------------------------- #

def ensure_role(name: str, description: str | None = None) -> Role:
    with db_session_context() as db:
        _require(db)
        role = db.query(Role).filter(Role.name == name).first()
        if not role:
            role = Role(name=name, description=description)
            db.add(role)
            db.commit()
            db.refresh(role)
        return role


def assign_global_role(user_id, role_name: str) -> bool:
    with db_session_context() as db:
        _require(db)
        role = db.query(Role).filter(Role.name == role_name).first()
        if not role:
            raise ValueError(f"Role {role_name} does not exist.")
        existing = (
            db.query(UserRole)
            .filter(UserRole.user_id == user_id, UserRole.role_id == role.id)
            .first()
        )
        if existing:
            return True
        db.add(UserRole(user_id=user_id, role_id=role.id))
        db.commit()
        return True


def remove_global_role(user_id, role_name: str) -> bool:
    with db_session_context() as db:
        _require(db)
        role = db.query(Role).filter(Role.name == role_name).first()
        if not role:
            return False
        db.query(UserRole).filter(
            UserRole.user_id == user_id, UserRole.role_id == role.id
        ).delete()
        db.commit()
        return True


# --------------------------------------------------------------------------- #
# Projects
# --------------------------------------------------------------------------- #

def list_projects() -> list[dict]:
    with db_session_context() as db:
        _require(db)
        return [_project_dict(p) for p in db.query(Project).order_by(Project.id).all()]


def get_project(project_id: str) -> dict | None:
    with db_session_context() as db:
        _require(db)
        p = db.query(Project).filter(Project.id == project_id).first()
        return _project_dict(p) if p else None


def create_project(
    *, project_id: str, name: str, description: str | None = None,
    domain_url: str | None = None, domain_owner: str | None = None,
    contact_email: str | None = None, audiences: list[str] | None = None,
    config_json: dict | None = None,
) -> dict:
    with db_session_context() as db:
        _require(db)
        if db.query(Project).filter(Project.id == project_id).first():
            raise ValueError(f"Project {project_id} already exists.")
        p = Project(
            id=project_id, name=name, description=description,
            domain_url=domain_url, domain_owner=domain_owner,
            contact_email=contact_email, config_json=config_json,
            enabled=True, status="active",
        )
        db.add(p)
        
        # Add audiences
        for aud in (audiences or ["general", "clinicians"]):
            db.add(ProjectAudience(project_id=project_id, audience=aud))
            
        db.commit()
        db.refresh(p)
        return _project_dict(p)


def update_project(project_id: str, **fields) -> dict | None:
    allowed = {"name", "description", "domain_url", "domain_owner", "contact_email", "enabled", "status", "config_json"}
    with db_session_context() as db:
        _require(db)
        p = db.query(Project).filter(Project.id == project_id).first()
        if not p:
            return None
        for key, value in fields.items():
            if key in allowed and value is not None:
                setattr(p, key, value)
        p.updated_at = datetime.datetime.utcnow()
        db.commit()
        db.refresh(p)
        return _project_dict(p)


def delete_project(project_id: str) -> bool:
    with db_session_context() as db:
        _require(db)
        p = db.query(Project).filter(Project.id == project_id).first()
        if not p:
            return False
        db.delete(p)  # cascades to memberships/audiences via FK
        db.commit()
        return True


# --------------------------------------------------------------------------- #
# Project memberships (project admins)
# --------------------------------------------------------------------------- #

def list_project_members(project_id: str) -> list[dict]:
    with db_session_context() as db:
        _require(db)
        rows = (
            db.query(ProjectMembership, User)
            .join(User, User.id == ProjectMembership.user_id)
            .filter(ProjectMembership.project_id == project_id)
            .all()
        )
        return [
            {
                "user_id": str(user.id),
                "email": user.email,
                "full_name": user.full_name,
                "membership_role": m.membership_role,
            }
            for m, user in rows
        ]


def add_project_membership(project_id: str, user_id, membership_role: str = ROLE_PROJECT_ADMIN) -> bool:
    with db_session_context() as db:
        _require(db)
        existing = (
            db.query(ProjectMembership)
            .filter(
                ProjectMembership.project_id == project_id,
                ProjectMembership.user_id == user_id,
                ProjectMembership.membership_role == membership_role,
            )
            .first()
        )
        if existing:
            return True
        db.add(
            ProjectMembership(
                project_id=project_id, user_id=user_id, membership_role=membership_role
            )
        )
        db.commit()
        return True


def remove_project_membership(project_id: str, user_id) -> bool:
    with db_session_context() as db:
        _require(db)
        deleted = (
            db.query(ProjectMembership)
            .filter(
                ProjectMembership.project_id == project_id,
                ProjectMembership.user_id == user_id,
            )
            .delete()
        )
        db.commit()
        return bool(deleted)


# --------------------------------------------------------------------------- #
# Ingestion Jobs
# --------------------------------------------------------------------------- #

def create_ingestion_job(
    *, project_id: str, audience: str | None = None, job_type: str, payload: dict | None = None
) -> str:
    from app.db.models import IngestionJob
    with db_session_context() as db:
        _require(db)
        job = IngestionJob(
            project_id=project_id,
            audience=audience,
            job_type=job_type,
            status="queued",
            payload=payload,
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return str(job.id)


def update_ingestion_job(job_id: str, status: str, error_message: str | None = None, finished: bool = False) -> None:
    from app.db.models import IngestionJob
    with db_session_context() as db:
        _require(db)
        job = db.query(IngestionJob).filter(IngestionJob.id == job_id).first()
        if not job:
            return
        job.status = status
        if error_message:
            job.error_message = error_message
        if status == "processing" and not job.started_at:
            job.started_at = datetime.datetime.utcnow()
        if finished:
            job.finished_at = datetime.datetime.utcnow()
        db.commit()


# --------------------------------------------------------------------------- #
# Index Runs
# --------------------------------------------------------------------------- #

def create_index_run(*, project_id: str, audience: str, embedding_model: str) -> str:
    from app.db.models import IndexRun
    with db_session_context() as db:
        _require(db)
        run = IndexRun(
            project_id=project_id,
            audience=audience,
            embedding_model=embedding_model,
            status="queued",
        )
        db.add(run)
        db.commit()
        db.refresh(run)
        return str(run.id)


def update_index_run(run_id: str, status: str, chunk_count: int = 0, error_message: str | None = None, finished: bool = False) -> None:
    from app.db.models import IndexRun
    with db_session_context() as db:
        _require(db)
        run = db.query(IndexRun).filter(IndexRun.id == run_id).first()
        if not run:
            return
        run.status = status
        if chunk_count:
            run.chunk_count = chunk_count
        if error_message:
            run.error_message = error_message
        if status == "processing" and not run.started_at:
            run.started_at = datetime.datetime.utcnow()
        if finished:
            run.finished_at = datetime.datetime.utcnow()
        db.commit()


def list_source_assets(project_id: str, audience: str) -> list[dict]:
    from app.db.models import SourceAsset
    with db_session_context() as db:
        _require(db)
        assets = (
            db.query(SourceAsset)
            .filter(SourceAsset.project_id == project_id, SourceAsset.audience == audience)
            .order_by(SourceAsset.created_at.desc())
            .all()
        )
        return [
            {
                "id": str(a.id),
                "source_name": a.source_name,
                "source_url": a.source_url,
                "source_file": a.source_file,
                "status": a.status,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in assets
        ]


# --------------------------------------------------------------------------- #
# Overview & Monitoring
# --------------------------------------------------------------------------- #

def get_platform_overview() -> dict:
    """Return high-level platform stats for Super Admins."""
    from app.db.models import AuditLog, ChatMessage, Project, User
    from sqlalchemy import func, cast, Date
    import datetime
    
    with db_session_context() as db:
        _require(db)
        
        # Activity data (last 14 days)
        fourteen_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=14)
        activity = db.query(
            cast(ChatMessage.created_at, Date).label("date"),
            func.count(ChatMessage.id).label("count")
        ).filter(
            ChatMessage.is_user == True,
            ChatMessage.created_at >= fourteen_days_ago
        ).group_by(cast(ChatMessage.created_at, Date)).order_by("date").all()
        
        # Toxicity stats
        toxic_count = db.query(ChatMessage).filter(
            ChatMessage.is_user == True,
            ChatMessage.toxicity_output != None,
            ChatMessage.toxicity_output['toxic'].astext == "true"
        ).count()
        
        # System health (simplified)
        from app.db.session import get_database_status
        health = {
            "database": get_database_status(),
            "last_audit": db.query(AuditLog).order_by(AuditLog.created_at.desc()).first().created_at.isoformat() if db.query(AuditLog).count() > 0 else None
        }
        
        total_msg = db.query(ChatMessage).filter(ChatMessage.is_user == True).count()

        return {
            "total_projects": db.query(Project).count(),
            "total_users": db.query(User).count(),
            "total_messages": total_msg,
            "toxic_messages": toxic_count,
            "system_health": health,
            "activity_data": [{"date": str(a.date), "count": a.count} for a in activity],
            "recent_audit_logs": list_audit_logs(limit=5),
        }


def get_project_overview(project_id: str) -> dict:
    """Return high-level stats for a specific project."""
    from app.db.models import ChatFeedback, ChatMessage, IngestionJob, SourceAsset
    from sqlalchemy import func, cast, Date
    import datetime
    
    with db_session_context() as db:
        _require(db)
        # Verify project exists
        p = db.query(Project).filter(Project.id == project_id).first()
        if not p:
            raise ValueError(f"Project {project_id} not found.")

        # Message count (user only)
        msg_count = db.query(ChatMessage).filter(
            ChatMessage.project_id == project_id,
            ChatMessage.is_user == True
        ).count()

        # Average rating
        avg_rating = db.query(func.avg(ChatFeedback.rating)).filter(
            ChatFeedback.project_id == project_id
        ).scalar()

        # Active jobs
        active_jobs = db.query(IngestionJob).filter(
            IngestionJob.project_id == project_id,
            IngestionJob.status.in_(["queued", "processing"])
        ).count()

        # Activity data (last 14 days)
        fourteen_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=14)
        activity = db.query(
            cast(ChatMessage.created_at, Date).label("date"),
            func.count(ChatMessage.id).label("count")
        ).filter(
            ChatMessage.project_id == project_id,
            ChatMessage.is_user == True,
            ChatMessage.created_at >= fourteen_days_ago
        ).group_by(cast(ChatMessage.created_at, Date)).order_by("date").all()

        return {
            "project_id": project_id,
            "project_name": p.name,
            "total_user_messages": msg_count,
            "average_rating": float(avg_rating) if avg_rating else 0.0,
            "total_sources": db.query(SourceAsset).filter(SourceAsset.project_id == project_id).count(),
            "active_ingestion_jobs": active_jobs,
            "activity_data": [{"date": str(a.date), "count": a.count} for a in activity],
            "recent_audit_logs": list_audit_logs(project_id=project_id, limit=5),
        }


def list_audit_logs(project_id: str | None = None, limit: int = 50) -> list[dict]:
    from app.db.models import AuditLog, User
    with db_session_context() as db:
        _require(db)
        query = db.query(AuditLog, User.email).outerjoin(User, User.id == AuditLog.actor_user_id)
        if project_id:
            query = query.filter(AuditLog.project_id == project_id)
        
        logs = query.order_by(AuditLog.created_at.desc()).limit(limit).all()
        return [
            {
                "id": str(log.id),
                "actor_email": email or "system",
                "action": log.action,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "project_id": log.project_id,
                "payload": log.payload,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log, email in logs
        ]


# --------------------------------------------------------------------------- #
# Audit log
# --------------------------------------------------------------------------- #

def record_audit(
    *, actor_user_id=None, project_id: str | None = None, action: str,
    entity_type: str | None = None, entity_id: str | None = None,
    payload: dict | None = None,
) -> None:
    """Best-effort audit write; never raises (logging an action must not break it)."""
    try:
        from sqlalchemy import text

        with db_session_context() as db:
            if db is None:
                return
            db.execute(
                text(
                    """
                    INSERT INTO audit_logs
                        (actor_user_id, project_id, action, entity_type, entity_id, payload)
                    VALUES
                        (:actor, :project_id, :action, :entity_type, :entity_id,
                         CAST(:payload AS JSONB))
                    """
                ),
                {
                    "actor": str(actor_user_id) if actor_user_id else None,
                    "project_id": project_id,
                    "action": action,
                    "entity_type": entity_type,
                    "entity_id": str(entity_id) if entity_id else None,
                    "payload": __import__("json").dumps(payload) if payload else None,
                },
            )
            db.commit()
    except Exception:  # noqa: BLE001
        logger.exception("Failed to record audit log for action=%s", action)


def _coerce_uuid(value) -> uuid_lib.UUID:
    """Parse a string user id into a UUID, raising ValueError on bad input."""
    if isinstance(value, uuid_lib.UUID):
        return value
    return uuid_lib.UUID(str(value))


def bootstrap_admin_defaults() -> None:
    """Ensure expected roles exist and optionally create the initial super admin."""
    ensure_role(ROLE_SUPER_ADMIN, "Full platform administrator.")
    ensure_role(ROLE_PROJECT_ADMIN, "Project-scoped knowledge-base administrator.")

    if not BOOTSTRAP_SUPER_ADMIN_EMAIL or not BOOTSTRAP_SUPER_ADMIN_PASSWORD:
        return

    from app.core.auth import hash_password

    email = BOOTSTRAP_SUPER_ADMIN_EMAIL.lower().strip()
    user = get_user_by_email(email)
    if user:
        assign_global_role(user.id, ROLE_SUPER_ADMIN)
        return

    created = create_user(
        email=email,
        full_name="Bootstrap Super Admin",
        password_hash=hash_password(BOOTSTRAP_SUPER_ADMIN_PASSWORD),
    )
    assign_global_role(_coerce_uuid(created["id"]), ROLE_SUPER_ADMIN)
