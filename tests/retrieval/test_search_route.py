from app.api.routes import search as search_routes
from app.schemas import SearchRequest


def test_search_general_route(monkeypatch):
    monkeypatch.setattr(search_routes, "guard_input", lambda text: (True, "SAFE", 0.1, None))
    monkeypatch.setattr(search_routes, "guard_output", lambda text: (True, "SAFE", 0.1, None))
    monkeypatch.setattr(
        search_routes,
        "search",
        lambda query, k, audience, project_id="tb": {
            "ids": [["general_doc_1"]],
            "documents": [["TB can spread through the air."]],
            "metadatas": [[{"source_file": "FAQ.md", "source_name": "FAQ", "source_url": "https://example.com"}]],
        },
    )

    response = search_routes.api_semantic_search_general(SearchRequest(query="How is TB spread?", k=1))

    body = response.model_dump()
    assert body["total_matches"] == 1
    assert body["matches"][0]["doc_id"] == "general_doc_1"
    assert body["matches"][0]["source_file"] == "FAQ.md"


def test_search_empty_results_returns_message(monkeypatch):
    monkeypatch.setattr(search_routes, "guard_input", lambda text: (True, "SAFE", 0.1, None))
    monkeypatch.setattr(search_routes, "guard_output", lambda text: (True, "SAFE", 0.1, None))
    monkeypatch.setattr(
        search_routes,
        "search",
        lambda query, k, audience, project_id="tb": {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
        },
    )

    response = search_routes.api_semantic_search_general(SearchRequest(query="unknown", k=1))
    body = response.model_dump()

    assert body["total_matches"] == 0
    assert body["matches"] == []
    assert body["message"] == "No relevant chunks were found for this query."
