import os
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import quote

import jwt
import requests
from dotenv import load_dotenv

from app.core.config import JWT_ALGORITHM, JWT_SECRET, ROLE_PROJECT_ADMIN, ROLE_SUPER_ADMIN

load_dotenv()


def get_keycloak_settings() -> dict[str, Any]:
    """Read Keycloak settings from the environment with compatibility aliases."""
    server_url = (
        os.getenv("KEYCLOAK_SERVER_URL")
        or os.getenv("KEYCLOAK_URL")
        or os.getenv("keycloak_url")
        or ""
    ).rstrip("/")

    realm = os.getenv("KEYCLOAK_REALM") or os.getenv("production_realm") or os.getenv("realm") or ""
    client_id = os.getenv("KEYCLOAK_CLIENT_ID") or os.getenv("production_client_id") or ""
    client_secret = os.getenv("KEYCLOAK_CLIENT_SECRET") or os.getenv("production_client_secret") or ""

    redirect_uri = (
        os.getenv("KEYCLOAK_REDIRECT_URI")
        or os.getenv("VITE_KEYCLOAK_REDIRECT_URI")
        or "http://localhost:3000/callback"
    )

    return {
        "server_url": server_url,
        "realm": realm,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "token_url": f"{server_url}/realms/{realm}/protocol/openid-connect/token" if server_url and realm else "",
        "jwks_url": f"{server_url}/realms/{realm}/protocol/openid-connect/certs" if server_url and realm else "",
    }


def create_access_token(payload: dict[str, Any], expires_minutes: int | None = None) -> str:
    now = datetime.utcnow()
    ttl = expires_minutes or int(os.getenv("JWT_EXPIRE_MINUTES", "720"))
    token_payload = {
        "iat": now,
        "exp": now + timedelta(minutes=ttl),
        **payload,
    }
    return jwt.encode(token_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


def get_keycloak_authorization_url(redirect_uri: str, state: str | None = None) -> str:
    settings = get_keycloak_settings()
    params = [
        "response_type=code",
        f"client_id={settings['client_id']}",
        f"redirect_uri={quote(redirect_uri, safe='')}",
        "scope=openid profile email",
    ]
    if state:
        params.append(f"state={quote(state, safe='')}")
    return f"{settings['server_url']}/realms/{settings['realm']}/protocol/openid-connect/auth?" + "&".join(params)


def map_keycloak_claims_to_app_context(claims: dict[str, Any]) -> dict[str, Any]:
    """Translate Keycloak claims into the shape used by the admin API."""
    candidate_roles: set[str] = set()

    def add_role(role_name: str | None) -> None:
        if not role_name:
            return
        normalized = str(role_name).strip().lower()
        if normalized in {ROLE_SUPER_ADMIN, ROLE_PROJECT_ADMIN}:
            candidate_roles.add(normalized)

    # Standard realm roles
    access_roles = claims.get("realm_access") or {}
    if isinstance(access_roles, dict):
        for role_name in access_roles.get("roles", []):
            add_role(role_name)

    # Direct roles claim and client roles commonly present in Keycloak tokens
    for role_name in claims.get("roles", []) or []:
        add_role(role_name)

    resource_access = claims.get("resource_access") or {}
    if isinstance(resource_access, dict):
        for client_roles in resource_access.values():
            if isinstance(client_roles, dict):
                for role_name in client_roles.get("roles", []) or []:
                    add_role(role_name)

    # Groups can be used to infer project or super-admin access in the realm
    for group_name in claims.get("groups", []) or []:
        if isinstance(group_name, str):
            add_role(group_name)

    if ROLE_SUPER_ADMIN in candidate_roles:
        role_names = [ROLE_SUPER_ADMIN]
    elif ROLE_PROJECT_ADMIN in candidate_roles:
        role_names = [ROLE_PROJECT_ADMIN]
    else:
        role_names = []

    return {
        "id": claims.get("sub") or "",
        "email": claims.get("email") or claims.get("preferred_username") or "",
        "full_name": claims.get("name") or claims.get("preferred_username") or "",
        "roles": role_names,
        "project_ids": [],
        "is_active": True,
        "permissions": [],
    }


def exchange_code_for_token(code: str, redirect_uri: str) -> dict[str, Any]:
    settings = get_keycloak_settings()
    token_url = settings["token_url"]
    data = {
        "grant_type": "authorization_code",
        "client_id": settings["client_id"],
        "client_secret": settings["client_secret"],
        "code": code,
        "redirect_uri": redirect_uri,
    }
    response = requests.post(token_url, data=data, timeout=20)
    response.raise_for_status()
    return response.json()


def get_keycloak_claims_from_token(token: str) -> dict[str, Any]:
    settings = get_keycloak_settings()
    if not settings["jwks_url"]:
        raise ValueError("Keycloak JWKS URL is not configured.")

    jwks_client = jwt.PyJWKClient(settings["jwks_url"])
    signing_key = jwks_client.get_signing_key_from_jwt(token)

    issuer = f"{settings['server_url']}/realms/{settings['realm']}"
    claims = jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=settings["client_id"],
        issuer=issuer,
        options={"require": ["exp", "iat", "sub"]},
    )
    return claims


def get_user_context_from_token(token: str) -> dict[str, Any] | None:
    try:
        return decode_access_token(token)
    except Exception:
        try:
            claims = get_keycloak_claims_from_token(token)
        except Exception:
            return None
        return map_keycloak_claims_to_app_context(claims)
