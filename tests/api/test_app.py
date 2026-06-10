from app.api.routes.health import health, ready


def test_health_endpoint():
    response = health()
    assert response.model_dump() == {"status": "ok"}


def test_ready_endpoint_exposes_database_status():
    body = ready()
    assert body["ready"] is True
    assert "database" in body
    assert "search" in body
