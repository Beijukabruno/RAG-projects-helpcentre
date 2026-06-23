import csv
import io
import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    hash_password,
    require_project_admin,
    require_super_admin,
)
from app.core.config import ROLE_PROJECT_ADMIN, ROLE_SUPER_ADMIN
from app.core.kb_admin import (
    add_knowledge_source,
    activate_source,
    process_ingestion_job,
    list_markdown_sources,
    remove_markdown_source,
)
from app.db import admin_repo
from app.db.admin_repo import DatabaseUnavailable
from app.db.persistence import get_last_records, get_last_records_for_project
from app.db.session import get_database_status


router = APIRouter(prefix="/admin", tags=["Admin"])


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1)


class UserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8)
    full_name: str | None = None
    role: str | None = Field(default=None, pattern="^(super_admin|project_admin)$")
    project_ids: list[str] = []


class UserActiveUpdate(BaseModel):
    is_active: bool


class RoleUpdate(BaseModel):
    role: str = Field(pattern="^(super_admin|project_admin)$")


class ProjectCreate(BaseModel):
    id: str = Field(min_length=2, max_length=64, pattern="^[a-zA-Z0-9_-]+$")
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    domain_url: str | None = None
    domain_owner: str | None = None
    contact_email: str | None = None
    audiences: list[str] = ["general", "clinicians"]
    config_json: dict[str, Any] | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    domain_url: str | None = None
    domain_owner: str | None = None
    contact_email: str | None = None
    enabled: bool | None = None
    status: str | None = None
    config_json: dict[str, Any] | None = None


class ProjectMembershipUpdate(BaseModel):
    user_id: str


def _handle_db_error(exc: DatabaseUnavailable):
    raise HTTPException(status_code=503, detail=str(exc)) from exc


def _parse_uuid(user_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(user_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid user id.") from exc


@router.post("/auth/login", tags=["Admin: Auth"])
def login(payload: LoginRequest):
    try:
        user = authenticate_user(payload.email, payload.password)
    except DatabaseUnavailable as exc:
        _handle_db_error(exc)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    return {"access_token": create_access_token(user), "token_type": "bearer", "user": user}


@router.get("/auth/me", tags=["Admin: Auth"])
def me(current_user: dict = Depends(get_current_user)):
    return current_user


@router.post("/users", dependencies=[Depends(require_super_admin)], tags=["Admin: Users"])
def create_user(payload: UserCreate):
    try:
        user = admin_repo.create_user(
            email=str(payload.email),
            full_name=payload.full_name,
            password_hash=hash_password(payload.password),
        )
        user_id = _parse_uuid(user["id"])
        if payload.role:
            admin_repo.assign_global_role(user_id, payload.role)
        if payload.role == ROLE_PROJECT_ADMIN:
            for project_id in payload.project_ids:
                admin_repo.add_project_membership(project_id, user_id, ROLE_PROJECT_ADMIN)
        admin_repo.record_audit(action="user.create", entity_type="user", entity_id=user["id"])
        return admin_repo.get_user_auth_context(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except DatabaseUnavailable as exc:
        _handle_db_error(exc)


@router.get("/users", dependencies=[Depends(require_super_admin)], tags=["Admin: Users"])
def list_users():
    try:
        return {"users": admin_repo.list_users()}
    except DatabaseUnavailable as exc:
        _handle_db_error(exc)


@router.patch("/users/{user_id}/active", dependencies=[Depends(require_super_admin)], tags=["Admin: Users"])
def set_user_active(user_id: str, payload: UserActiveUpdate):
    try:
        if not admin_repo.set_user_active(_parse_uuid(user_id), payload.is_active):
            raise HTTPException(status_code=404, detail="User not found.")
        admin_repo.record_audit(action="user.active.update", entity_type="user", entity_id=user_id)
        return {"ok": True}
    except DatabaseUnavailable as exc:
        _handle_db_error(exc)


@router.delete("/users/{user_id}", dependencies=[Depends(require_super_admin)], tags=["Admin: Users"])
def delete_user(user_id: str):
    try:
        if not admin_repo.delete_user(_parse_uuid(user_id)):
            raise HTTPException(status_code=404, detail="User not found.")
        admin_repo.record_audit(action="user.delete", entity_type="user", entity_id=user_id)
        return {"ok": True}
    except DatabaseUnavailable as exc:
        _handle_db_error(exc)


@router.post("/users/{user_id}/roles", dependencies=[Depends(require_super_admin)], tags=["Admin: Users"])
def add_user_role(user_id: str, payload: RoleUpdate):
    try:
        admin_repo.assign_global_role(_parse_uuid(user_id), payload.role)
        admin_repo.record_audit(action="user.role.add", entity_type="user", entity_id=user_id, payload=payload.model_dump())
        return {"ok": True}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DatabaseUnavailable as exc:
        _handle_db_error(exc)


@router.delete("/users/{user_id}/roles/{role}", dependencies=[Depends(require_super_admin)], tags=["Admin: Users"])
def remove_user_role(user_id: str, role: str):
    if role not in {ROLE_SUPER_ADMIN, ROLE_PROJECT_ADMIN}:
        raise HTTPException(status_code=400, detail="Unsupported role.")
    try:
        admin_repo.remove_global_role(_parse_uuid(user_id), role)
        admin_repo.record_audit(action="user.role.remove", entity_type="user", entity_id=user_id, payload={"role": role})
        return {"ok": True}
    except DatabaseUnavailable as exc:
        _handle_db_error(exc)


@router.get("/projects", dependencies=[Depends(require_super_admin)], tags=["Admin: Projects"])
def list_projects():
    try:
        return {"projects": admin_repo.list_projects()}
    except DatabaseUnavailable as exc:
        _handle_db_error(exc)


@router.post("/projects", dependencies=[Depends(require_super_admin)], tags=["Admin: Projects"])
def create_project(payload: ProjectCreate):
    try:
        project = admin_repo.create_project(
            project_id=payload.id,
            name=payload.name,
            description=payload.description,
            domain_url=payload.domain_url,
            domain_owner=payload.domain_owner,
            contact_email=payload.contact_email,
            audiences=payload.audiences,
            config_json=payload.config_json,
        )
        admin_repo.record_audit(action="project.create", entity_type="project", entity_id=payload.id)
        return project
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except DatabaseUnavailable as exc:
        _handle_db_error(exc)


@router.get("/projects/{project_id}", tags=["Admin: Projects"])
def get_project(project_id: str, current_user: dict = Depends(require_project_admin)):
    try:
        project = admin_repo.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found.")
        return project
    except DatabaseUnavailable as exc:
        _handle_db_error(exc)


@router.patch("/projects/{project_id}", dependencies=[Depends(require_super_admin)], tags=["Admin: Projects"])
def update_project(project_id: str, payload: ProjectUpdate):
    try:
        project = admin_repo.update_project(project_id, **payload.model_dump(exclude_unset=True))
        if not project:
            raise HTTPException(status_code=404, detail="Project not found.")
        admin_repo.record_audit(action="project.update", entity_type="project", entity_id=project_id)
        return project
    except DatabaseUnavailable as exc:
        _handle_db_error(exc)


@router.delete("/projects/{project_id}", dependencies=[Depends(require_super_admin)], tags=["Admin: Projects"])
def delete_project(project_id: str):
    try:
        if not admin_repo.delete_project(project_id):
            raise HTTPException(status_code=404, detail="Project not found.")
        admin_repo.record_audit(action="project.delete", entity_type="project", entity_id=project_id)
        return {"ok": True}
    except DatabaseUnavailable as exc:
        _handle_db_error(exc)


@router.get("/projects/{project_id}/admins", tags=["Admin: Projects"])
def list_project_admins(project_id: str, current_user: dict = Depends(require_project_admin)):
    try:
        return {"project_id": project_id, "admins": admin_repo.list_project_members(project_id)}
    except DatabaseUnavailable as exc:
        _handle_db_error(exc)


@router.post("/projects/{project_id}/admins", dependencies=[Depends(require_super_admin)], tags=["Admin: Projects"])
def add_project_admin(project_id: str, payload: ProjectMembershipUpdate):
    try:
        user_id = _parse_uuid(payload.user_id)
        admin_repo.assign_global_role(user_id, ROLE_PROJECT_ADMIN)
        admin_repo.add_project_membership(project_id, user_id, ROLE_PROJECT_ADMIN)
        admin_repo.record_audit(action="project.admin.add", project_id=project_id, entity_type="user", entity_id=payload.user_id)
        return {"ok": True}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DatabaseUnavailable as exc:
        _handle_db_error(exc)


@router.delete("/projects/{project_id}/admins/{user_id}", dependencies=[Depends(require_super_admin)], tags=["Admin: Projects"])
def remove_project_admin(project_id: str, user_id: str):
    try:
        admin_repo.remove_project_membership(project_id, _parse_uuid(user_id))
        admin_repo.record_audit(action="project.admin.remove", project_id=project_id, entity_type="user", entity_id=user_id)
        return {"ok": True}
    except DatabaseUnavailable as exc:
        _handle_db_error(exc)


@router.get("/projects/{project_id}/knowledge-base", tags=["Admin: Knowledge Base"])
def list_knowledge_base(project_id: str, audience: str = "general", current_user: dict = Depends(require_project_admin)):
    # Return both disk-based sources (legacy/manual) and DB-tracked assets
    return {
        "project_id": project_id, 
        "audience": audience, 
        "sources": list_markdown_sources(project_id, audience),
        "assets": admin_repo.list_source_assets(project_id, audience)
    }


@router.post("/projects/{project_id}/knowledge-base", tags=["Admin: Knowledge Base"])
async def upload_knowledge_base_source(
    project_id: str,
    background_tasks: BackgroundTasks,
    audience: str = Form("general"),
    source_name: str | None = Form(None),
    source_url: str | None = Form(None),
    file: UploadFile = File(...),
    current_user: dict = Depends(require_project_admin),
):
    try:
        result = await add_knowledge_source(
            project_id=project_id,
            audience=audience,
            upload=file,
            source_name=source_name,
            source_url=source_url,
            actor_user_id=current_user["id"],
        )
        
        # Trigger background processing (PDF to MD, etc.)
        background_tasks.add_task(process_ingestion_job, result["job_id"])
        
        admin_repo.record_audit(
            actor_user_id=current_user["id"],
            project_id=project_id,
            action="knowledge_base.source.upload",
            entity_type="source",
            entity_id=result["file_name"],
            payload={"audience": audience, "job_id": result["job_id"], "asset_id": result["asset_id"]},
        )
        return result
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except DatabaseUnavailable as exc:
        _handle_db_error(exc)


@router.post("/projects/{project_id}/knowledge-base/{asset_id}/activate", tags=["Admin: Knowledge Base"])
async def activate_knowledge_base_source(
    project_id: str,
    asset_id: str,
    audience: str = "general",
    current_user: dict = Depends(require_project_admin),
):
    try:
        result = await activate_source(project_id, audience, asset_id)
        admin_repo.record_audit(
            actor_user_id=current_user["id"],
            project_id=project_id,
            action="knowledge_base.source.activate",
            entity_type="source",
            entity_id=asset_id,
            payload={"audience": audience, "index_run_id": result["index_run_id"], "chunk_count": result["chunk_count"]},
        )
        return result
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/projects/{project_id}/knowledge-base/{file_name}", tags=["Admin: Knowledge Base"])
def delete_knowledge_base_source(
    project_id: str,
    file_name: str,
    audience: str = "general",
    current_user: dict = Depends(require_project_admin),
):
    try:
        result = remove_markdown_source(project_id, audience, file_name)
        admin_repo.record_audit(
            actor_user_id=current_user["id"],
            project_id=project_id,
            action="knowledge_base.source.remove",
            entity_type="source",
            entity_id=file_name,
            payload={"audience": audience, **result},
        )
        return result
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


# --------------------------------------------------------------------------- #
# Monitoring & Overview
# --------------------------------------------------------------------------- #

@router.get("/overview", tags=["Admin: Monitoring"], dependencies=[Depends(require_super_admin)])
def platform_overview():
    """High-level platform statistics for Super Admins."""
    try:
        return admin_repo.get_platform_overview()
    except DatabaseUnavailable as exc:
        _handle_db_error(exc)


@router.get("/projects/{project_id}/overview", tags=["Admin: Monitoring"])
def project_overview(project_id: str, current_user: dict = Depends(require_project_admin)):
    """High-level statistics for a specific project."""
    try:
        return admin_repo.get_project_overview(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DatabaseUnavailable as exc:
        _handle_db_error(exc)


@router.get("/audit-logs", tags=["Admin: Monitoring"], dependencies=[Depends(require_super_admin)])
def list_audit_logs(limit: int = 50):
    """Retrieve global audit logs for Super Admins."""
    try:
        return {"logs": admin_repo.list_audit_logs(limit=limit)}
    except DatabaseUnavailable as exc:
        _handle_db_error(exc)


@router.get("/toxicity-feed", tags=["Admin: Monitoring"], dependencies=[Depends(require_super_admin)])
def toxicity_feed(limit: int = 50):
    """Retrieve messages flagged as toxic."""
    from app.db.session import db_session_context
    from app.db.models import ChatMessage
    from sqlalchemy import func
    with db_session_context() as db:
        if db is None:
            raise HTTPException(status_code=503, detail="Database unavailable.")
        msgs = db.query(ChatMessage).filter(
            ChatMessage.toxicity_output != None,
            func.json_extract_path_text(ChatMessage.toxicity_output, "toxic") == "true"
        ).order_by(ChatMessage.created_at.desc()).limit(limit).all()
        
        return {
            "messages": [
                {
                    "id": str(m.id),
                    "project_id": m.project_id,
                    "message": m.message,
                    "toxicity": m.toxicity_output,
                    "created_at": m.created_at.isoformat()
                }
                for m in msgs
            ]
        }


@router.get("/projects/{project_id}/audit-logs", tags=["Admin: Monitoring"])
def list_project_audit_logs(project_id: str, limit: int = 50, current_user: dict = Depends(require_project_admin)):
    """Retrieve audit logs for a specific project."""
    try:
        return {"project_id": project_id, "logs": admin_repo.list_audit_logs(project_id=project_id, limit=limit)}
    except DatabaseUnavailable as exc:
        _handle_db_error(exc)


@router.get("/last-records", include_in_schema=False, tags=["Admin: Logs"])
def get_last_records_endpoint(n: int = 100, current_user: dict = Depends(require_super_admin)):
    return {"database": get_database_status(), "records": get_last_records(n)}


@router.get("/projects/{project_id}/last-records", include_in_schema=False, tags=["Admin: Logs"])
def get_project_last_records(
    project_id: str,
    n: int = 5,
    audience: str | None = None,
    current_user: dict = Depends(require_project_admin),
):
    return {
        "database": get_database_status(),
        "project_id": project_id,
        "audience": audience,
        "records": get_last_records_for_project(project_id, audience=audience, limit=n),
    }


@router.get("/last-records-csv", include_in_schema=False, tags=["Admin: Logs"])
def get_last_records_csv(n: int = 100, current_user: dict = Depends(require_super_admin)):
    records = get_last_records(n)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "id",
            "session_id",
            "is_user",
            "message",
            "llm_prompt",
            "llm_model",
            "llm_answer",
            "sources",
            "toxicity_input",
            "toxicity_output",
            "created_at",
        ]
    )
    for record in records:
        writer.writerow(
            [
                record.get("id"),
                record.get("session_id"),
                record.get("is_user"),
                record.get("message"),
                record.get("llm_prompt"),
                record.get("llm_model"),
                record.get("llm_answer"),
                record.get("sources"),
                record.get("toxicity_input"),
                record.get("toxicity_output"),
                record.get("created_at"),
            ]
        )
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=last_records.csv"},
    )


@router.get("/projects/{project_id}/last-records-csv", include_in_schema=False, tags=["Admin: Logs"])
def get_project_last_records_csv(
    project_id: str,
    n: int = 5,
    audience: str | None = None,
    current_user: dict = Depends(require_project_admin),
):
    records = get_last_records_for_project(project_id, audience=audience, limit=n)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "id",
            "session_id",
            "project_id",
            "audience",
            "is_user",
            "message",
            "llm_prompt",
            "llm_model",
            "llm_answer",
            "sources",
            "toxicity_input",
            "toxicity_output",
            "created_at",
        ]
    )
    for record in records:
        writer.writerow(
            [
                record.get("id"),
                record.get("session_id"),
                record.get("project_id"),
                record.get("audience"),
                record.get("is_user"),
                record.get("message"),
                record.get("llm_prompt"),
                record.get("llm_model"),
                record.get("llm_answer"),
                record.get("sources"),
                record.get("toxicity_input"),
                record.get("toxicity_output"),
                record.get("created_at"),
            ]
        )
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={project_id}_last_records.csv"},
    )
