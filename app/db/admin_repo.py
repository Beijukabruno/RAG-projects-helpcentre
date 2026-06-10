"""Data-access helpers for admin: users, roles, projects, memberships, audit.

All functions use the shared `db_session_context`. They raise RuntimeError when
the database is unavailable so callers can surface a clear 503, rather than
silently returning empty data (admin operations must not pretend to succeed).
"""

import datetime
import logging
import uuid as uuid_lib

from app.core.config import ROLE_PROJECT_ADMIN, ROLE_SUPER_ADMIN
from app.db.models import (
    Project,
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
        "enabled": p.enabled,
        "status": p.status,
        "config_json": p.config_json,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
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
    domain_url: str | None = None, config_json: dict | None = None,
) -> dict:
    with db_session_context() as db:
        _require(db)
        if db.query(Project).filter(Project.id == project_id).first():
            raise ValueError(f"Project {project_id} already exists.")
        p = Project(
            id=project_id, name=name, description=description,
            domain_url=domain_url, config_json=config_json,
            enabled=True, status="active",
        )
        db.add(p)
        db.commit()
        db.refresh(p)
        return _project_dict(p)


def update_project(project_id: str, **fields) -> dict | None:
    allowed = {"name", "description", "domain_url", "enabled", "status", "config_json"}
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
