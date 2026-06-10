from app.core.chat_history import InMemoryChatMessageHistory
from app.core.project_manager import project_manager


def _build_shared_instructions(project_id: str, audience: str) -> str:
    system_role = project_manager.get_system_role(project_id)
    prompt_rules = project_manager.get_prompt_rules(project_id)
    return (
        f"{system_role}\n"
        f"Audience: {audience}.\n"
        "Answer using ONLY the provided information and the current conversation when it is relevant.\n"
        "Write a clean, user-facing response for a web interface.\n"
        "Do not include raw markdown citations, raw URLs, or bracketed source references in the answer body.\n"
        "Do not invent facts, recommendations, dosages, or clinical guidance that are not supported by the retrieved context.\n"
        "If the retrieved information is incomplete, say what is known and clearly note the limitation.\n"
        "Prefer this style:\n"
        "- Start with a direct answer in 3-5 sentences.\n"
        "- Add a second paragraph only if it helps.\n"
        "- Use bullet points only when they improve clarity.\n"
        "- Keep the wording calm, clear, and natural.\n"
        "- Do not mention retrieval, chunks, source numbers, or knowledge base names.\n"
        "- Keep the tone appropriate for the selected audience.\n"
        + ("" if not prompt_rules else "\nProject-specific rules:\n" + "\n".join(f"- {rule}" for rule in prompt_rules) + "\n")
    )


def build_prompt(project_id: str, audience: str, user_query: str, results: dict) -> str:
    prompt = _build_shared_instructions(project_id, audience)
    prompt += f"\nQuestion: {user_query}\n\nRelevant Information:\n"

    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    for index, (doc, meta) in enumerate(zip(docs, metas), 1):
        src_name = meta.get("source_name", "")
        src_url = meta.get("source_url", "")
        prompt += f"{index}. {doc}\n(Source: {src_name}, URL: {src_url})\n"

    prompt += "\nYour answer:"
    return prompt


def build_prompt_with_history(
    project_id: str,
    audience: str,
    user_query: str,
    results: dict,
    chat_history: InMemoryChatMessageHistory,
    history_limit: int = 3,
) -> str:
    prompt = _build_shared_instructions(project_id, audience)

    history = chat_history.messages[-history_limit * 3 :]
    if history:
        prompt += "\nPrevious conversation:\n"
        for msg in history:
            role = msg.type.capitalize()
            prompt += f"{role}: {msg.content}\n"
        prompt += "\n"

    prompt += f"Question: {user_query}\n\nRelevant Information:\n"
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    for index, (doc, meta) in enumerate(zip(docs, metas), 1):
        src_name = meta.get("source_name", "")
        src_url = meta.get("source_url", "")
        prompt += f"{index}. {doc}\n(Source: {src_name}, URL: {src_url})\n"

    prompt += "\nYour answer:"
    return prompt
