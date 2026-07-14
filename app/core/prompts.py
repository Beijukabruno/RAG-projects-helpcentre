from app.core.chat_history import InMemoryChatMessageHistory
from app.core.project_manager import project_manager

PROMPT_TEMPLATE = """You are an expert tutor for the {project_id} help-centre domain, answering for the {audience} audience.

System role:
{system_role}

Project-specific guidance:
{project_rules}

Retrieved content:
{retrieved_content}

Conversation history:
{conversation_history}

User question:
{user_query}

Instructions:
1. Answer the question directly in the first sentence.
2. Use only the retrieved content and relevant conversation history.
3. If evidence is incomplete, state clearly what is known and what is missing.
4. Do not invent facts, dosages, or recommendations.
5. Keep the response clear, structured, and audience-appropriate.

Answer:
"""


def _format_project_rules(project_id: str) -> str:
    rules = project_manager.get_prompt_rules(project_id)
    if not rules:
        return "- No additional project rules."
    return "\n".join(f"- {rule}" for rule in rules)


def _format_retrieved_content(results: dict) -> str:
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    if not docs:
        return "- No retrieved content available."

    lines: list[str] = []
    for index, (doc, meta) in enumerate(zip(docs, metas), 1):
        src_name = meta.get("source_name", "")
        src_url = meta.get("source_url", "")
        lines.append(f"{index}. {doc}\n(Source: {src_name}, URL: {src_url})")
    return "\n".join(lines)


def _format_history(project_id: str, chat_history: InMemoryChatMessageHistory, history_limit: int) -> str:
    include_history = project_manager.get_feature_flag(project_id, "chat_history_enabled", default=True)
    history = chat_history.messages[-history_limit * 3 :] if include_history else []
    if not history:
        return "- No prior conversation history used."

    lines = []
    for msg in history:
        role = msg.type.capitalize()
        lines.append(f"{role}: {msg.content}")
    return "\n".join(lines)


def _build_prompt(
    *,
    project_id: str,
    audience: str,
    user_query: str,
    results: dict,
    conversation_history: str,
) -> str:
    return PROMPT_TEMPLATE.format(
        project_id=project_id,
        audience=audience,
        system_role=project_manager.get_system_role(project_id),
        project_rules=_format_project_rules(project_id),
        retrieved_content=_format_retrieved_content(results),
        conversation_history=conversation_history,
        user_query=user_query,
    )


def build_prompt(project_id: str, audience: str, user_query: str, results: dict) -> str:
    return _build_prompt(
        project_id=project_id,
        audience=audience,
        conversation_history="- No prior conversation history used.",
        user_query=user_query,
        results=results,
    )


def build_prompt_with_history(
    project_id: str,
    audience: str,
    user_query: str,
    results: dict,
    chat_history: InMemoryChatMessageHistory,
    history_limit: int = 3,
) -> str:
    return _build_prompt(
        project_id=project_id,
        audience=audience,
        conversation_history=_format_history(project_id, chat_history, history_limit),
        user_query=user_query,
        results=results,
    )
