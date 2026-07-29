from app.retrieval import semantic_search


def test_build_retrieval_query_expands_registration_terms():
    query = "How do I register a client?"

    expanded = semantic_search.build_retrieval_query(query)

    lowered = expanded.lower()
    assert "register" in lowered
    assert "client" in lowered
    assert any(term in lowered for term in ["enroll", "add", "create"])
