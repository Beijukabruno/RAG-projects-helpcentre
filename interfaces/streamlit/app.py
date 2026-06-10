import os
import requests
import streamlit as st


DEFAULT_API_BASE = os.getenv("TB_HELP_API_BASE", "http://localhost:8000")


def post_json(url: str, payload: dict, timeout: int = 60):
    response = requests.post(url, json=payload, timeout=timeout)
    if response.status_code >= 400:
        raise RuntimeError(f"{response.status_code} - {response.text}")
    return response.json()


def audience_to_chat_path(audience: str) -> str:
    return "/chat/general" if audience == "general" else "/chat/clinicians"


def audience_to_search_path(audience: str) -> str:
    return "/api/search/general" if audience == "general" else "/api/search/clinicians"


def render_sources(sources: list[dict]):
    """Render source citations with default message if none available."""
    if not sources:
        st.info("No supporting sources were retrieved for this answer. "
                "This may indicate limited relevant information in the knowledge base.")
        return

    st.markdown("### Sources")
    for index, src in enumerate(sources, start=1):
        header = src.get("header") or "Untitled"
        source_file = src.get("source_file") or "Unknown file"
        source_url = src.get("source_url")
        excerpt = src.get("excerpt") or ""

        st.markdown(f"**{index}. {header}**")
        st.caption(source_file)
        if source_url:
            st.markdown(f"[Reference Link]({source_url})")
        if excerpt:
            st.write(excerpt)
        st.divider()


def render_matches(matches: list[dict]):
    """Render matched chunks with default message if none available."""
    if not matches:
        st.info("No relevant documents found for your search query. "
                "Try rewording your question or using different terms.")
        return

    st.markdown("### Retrieved Chunks")
    for index, match in enumerate(matches, start=1):
        header = match.get("header") or "Untitled"
        source_file = match.get("source_file") or "Unknown file"
        link = match.get("link")
        markdown = match.get("markdown") or ""

        st.markdown(f"**{index}. {header}**")
        st.caption(source_file)
        if link:
            st.markdown(f"[Reference Link]({link})")
        if markdown:
            st.write(markdown)
        st.divider()


st.set_page_config(page_title="TB Help Centre", layout="wide")
st.title("TB Help Centre Interface")
st.caption("Audience-aware Chatbot and Semantic Search client")

with st.sidebar:
    st.header("Connection")
    api_base = st.text_input("API Base URL", value=DEFAULT_API_BASE).rstrip("/")
    audience = st.selectbox("Audience", options=["general", "clinicians"], index=0)
    k = st.slider("Top K", min_value=1, max_value=20, value=5)
    st.markdown("---")
    st.caption("Use the same API URL locally and in deployment.")

tab_chat, tab_search = st.tabs(["Chatbot", "Semantic Search"])

with tab_chat:
    st.subheader("Ask a Question")
    question = st.text_area(
        "Question",
        placeholder="e.g. How is TB spread?",
        height=120,
    )

    if st.button("Get Chat Answer", type="primary"):
        if not question.strip():
            st.warning("Please enter a question.")
        else:
            with st.spinner("Generating answer..."):
                try:
                    endpoint = f"{api_base}{audience_to_chat_path(audience)}"
                    payload = {"question": question.strip(), "k": k}
                    data = post_json(endpoint, payload)

                    answer = data.get("answer", "").strip()
                    if not answer:
                        st.warning("No answer could be generated. "
                                   "This may indicate insufficient information in the knowledge base "
                                   "or that the query does not match available content.")
                    else:
                        st.markdown("### Answer")
                        st.write(answer)

                    meta = data.get("meta", {})
                    if meta:
                        matched = meta.get('matched_chunks', 0)
                        total = meta.get('total_chunks', 'n/a')
                        st.caption(f"matched_chunks: {matched} | total_chunks: {total}")

                    render_sources(data.get("sources", []))
                except Exception as exc:
                    st.error(f"Request failed: {exc}")
                    st.caption("Try checking that the API is running at the specified URL.")

with tab_search:
    st.subheader("Retrieve Relevant Chunks")
    search_query = st.text_area(
        "Query",
        placeholder="e.g. What are signs and symptoms of TB?",
        height=120,
    )

    if st.button("Run Semantic Search"):
        if not search_query.strip():
            st.warning("Please enter a query.")
        else:
            with st.spinner("Searching..."):
                try:
                    endpoint = f"{api_base}{audience_to_search_path(audience)}"
                    payload = {"query": search_query.strip(), "k": k}
                    data = post_json(endpoint, payload)

                    total_matches = data.get('total_matches', 0)
                    if total_matches == 0:
                        st.info("No matches found. The search returned no relevant documents. "
                                "Consider:\n"
                                "- Using simpler or different keywords\n"
                                "- Checking the audience selection\n"
                                "- Trying a related topic")
                    else:
                        st.caption(f"total_matches: {total_matches}")
                    
                    render_matches(data.get("matches", []))
                except Exception as exc:
                    st.error(f"Request failed: {exc}")
                    st.caption("Try checking that the API is running at the specified URL.")
