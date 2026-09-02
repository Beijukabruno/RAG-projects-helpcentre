import os

from app.core.keycloak_auth import (
    create_access_token,
    decode_access_token,
    exchange_code_for_token,
    get_keycloak_settings,
    map_keycloak_claims_to_app_context,
)


def test_get_keycloak_settings_falls_back_to_supported_names(monkeypatch):
    monkeypatch.delenv("KEYCLOAK_SERVER_URL", raising=False)
    monkeypatch.delenv("KEYCLOAK_URL", raising=False)
    monkeypatch.setenv("keycloak_url", "https://dsi-keycloak.marconilab.org")
    monkeypatch.setenv("production_realm", "helpcentre")

    settings = get_keycloak_settings()

    assert settings["server_url"] == "https://dsi-keycloak.marconilab.org"
    assert settings["realm"] == "helpcentre"


def test_create_and_decode_access_token_round_trip():
    token = create_access_token({"sub": "user-1", "email": "demo@example.com"})
    payload = decode_access_token(token)

    assert payload["sub"] == "user-1"
    assert payload["email"] == "demo@example.com"


def test_map_keycloak_claims_to_app_context_uses_admin_roles():
    context = map_keycloak_claims_to_app_context(
        {
            "sub": "kc-user-1",
            "email": "demo@example.com",
            "preferred_username": "demo",
            "realm_access": {"roles": ["super_admin", "offline_access"]},
        }
    )

    assert context["email"] == "demo@example.com"
    assert context["roles"] == ["super_admin"]
    assert context["is_active"] is True


def test_exchange_code_for_token_returns_access_token(monkeypatch):
    class DummyResponse:
        def __init__(self, payload, status_code=200):
            self._payload = payload
            self.status_code = status_code

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    def fake_post(url, data, headers=None, timeout=None):
        assert url.endswith("/protocol/openid-connect/token")
        assert data["code"] == "demo-code"
        return DummyResponse({"access_token": "abc123"})

    monkeypatch.setattr("app.core.keycloak_auth.requests.post", fake_post)
    monkeypatch.setenv("KEYCLOAK_SERVER_URL", "https://dsi-keycloak.marconilab.org")
    monkeypatch.setenv("KEYCLOAK_REALM", "helpcentre")
    monkeypatch.setenv("KEYCLOAK_CLIENT_ID", "helpcentre-backend")
    monkeypatch.setenv("KEYCLOAK_CLIENT_SECRET", "secret")

    result = exchange_code_for_token("demo-code", "http://localhost:3000/callback")

    assert result["access_token"] == "abc123"


def test_map_keycloak_claims_to_app_context_uses_groups_and_client_roles():
    context = map_keycloak_claims_to_app_context(
        {
            "sub": "kc-user-2",
            "email": "ops@example.com",
            "preferred_username": "ops",
            "groups": ["project_admin"],
            "resource_access": {"helpcentre-admin": {"roles": ["super_admin"]}},
        }
    )

    assert context["roles"] == ["super_admin"]
    assert context["is_active"] is True
