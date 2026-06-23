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
        "iat": now,
        "exp": now + datetime.timedelta(minutes=JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def authenticate_user(email: str, password: str) -> dict | None:
    user = admin_repo.get_user_by_email(email)
    if not user or not user.is_active or not verify_password(password, user.password_hash):
        return None
    return admin_repo.get_user_auth_context(user.id)


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
    return user


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
