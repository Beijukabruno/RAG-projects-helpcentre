import datetime
import uuid

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.config import (
    JWT_ALGORITHM,
    JWT_EXPIRE_MINUTES,
    JWT_SECRET,
    ROLE_PROJECT_ADMIN,
    ROLE_SUPER_ADMIN,
)
from app.db import admin_repo
from app.db.admin_repo import DatabaseUnavailable


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/admin/auth/login")


ACTION_PERMISSIONS_BY_ROLE = {
    ROLE_SUPER_ADMIN: {"*"},
    ROLE_PROJECT_ADMIN: {
        "project.read",
        "project.feature_flags.read",
        "project.admins.read",
        "project.monitor.read",
        "project.logs.read",
        "project.logs.export",
        "kb.read",
    },
}


def _build_permissions(roles: list[str]) -> list[str]:
    perms: set[str] = set()
    for role in roles:
        perms.update(ACTION_PERMISSIONS_BY_ROLE.get(role, set()))
    return sorted(perms)


def _with_permissions(user: dict) -> dict:
    roles = user.get("roles", [])
    return {**user, "permissions": _build_permissions(roles)}


def _has_action_permission(current_user: dict, action: str, project_id: str | None = None) -> bool:
    permissions = set(current_user.get("permissions", []))
    if "*" not in permissions and action not in permissions:
        return False

    if project_id is not None and ROLE_SUPER_ADMIN not in current_user.get("roles", []):
        return project_id in current_user.get("project_ids", [])
    return True


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user: dict) -> str:
    now = datetime.datetime.utcnow()
    payload = {
        "sub": user["id"],
        "email": user["email"],
        "roles": user.get("roles", []),
        "project_ids": user.get("project_ids", []),
        "permissions": user.get("permissions", []),
        "iat": now,
        "exp": now + datetime.timedelta(minutes=JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def authenticate_user(email: str, password: str) -> dict | None:
    user = admin_repo.get_user_by_email(email)
    if not user or not user.is_active or not verify_password(password, user.password_hash):
        return None
    auth_context = admin_repo.get_user_auth_context(user.id)
    return _with_permissions(auth_context) if auth_context else None


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = uuid.UUID(str(payload.get("sub")))
    except Exception as exc:
        raise credentials_error from exc

    try:
        user = admin_repo.get_user_auth_context(user_id)
    except DatabaseUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if not user or not user.get("is_active"):
        raise credentials_error
    return _with_permissions(user)


def require_global_action(action: str):
    def _dependency(current_user: dict = Depends(get_current_user)) -> dict:
        if not _has_action_permission(current_user, action):
            raise HTTPException(status_code=403, detail=f"Permission denied: {action}")
        return current_user

    return _dependency


def require_project_action(action: str):
    def _dependency(project_id: str, current_user: dict = Depends(get_current_user)) -> dict:
        if not _has_action_permission(current_user, action, project_id=project_id):
            raise HTTPException(status_code=403, detail=f"Permission denied: {action}")
        return current_user

    return _dependency


def require_super_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if ROLE_SUPER_ADMIN not in current_user.get("roles", []):
        raise HTTPException(status_code=403, detail="Super admin access required.")
    return current_user


def require_project_admin(project_id: str, current_user: dict = Depends(get_current_user)) -> dict:
    roles = current_user.get("roles", [])
    if ROLE_SUPER_ADMIN in roles:
        return current_user
    if ROLE_PROJECT_ADMIN in roles and project_id in current_user.get("project_ids", []):
        return current_user
    raise HTTPException(status_code=403, detail="Project admin access required.")
