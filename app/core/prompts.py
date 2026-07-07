from app.core.chat_history import InMemoryChatMessageHistory
from app.core.project_manager import project_manager


DEFAULT_RESPONSE_POLICY = [
    "Answer the user's question directly in the first sentence.",
    "Synthesize the answer from the retrieved context; do not summarize the document structure.",
    "Never tell the user to consult a manual, source document, or knowledge base before answering.",
    "Do not mention retrieved chunks, source numbers, or raw citation markup in the answer body.",
    "Preserve exact medical terminology, names of tests, medication names, screen labels, and official terms.",
    "Do not invent facts, steps, recommendations, dosages, or clinical guidance that are not supported by the context.",
    "If the context is incomplete, say what is known and clearly state what is missing.",
    "Keep the response concise unless the user asks for more detail.",
]

DEFAULT_ANSWER_STYLE = [
    "Use short paragraphs and plain language.",
    "Use numbered steps for procedures and workflows.",
    "Use bullet points only when they improve clarity.",
    "Use headings only when they help the user scan the answer.",
    "Do not copy long passages verbatim unless exact wording matters.",
]

DEFAULT_QUESTION_TYPES = [
    "procedure",
    "troubleshooting",
    "definition",
    "explanation",
    "comparison",
    "diagnosis",
    "treatment",
    "prevention",
    "eligibility",
    "workflow",
    "policy",
    "navigation",
    "faq",
]


def _coerce_lines(value, fallback):
    if isinstance(value, str):
        lines = [value.strip()] if value.strip() else []
    elif isinstance(value, list):
        lines = [str(item).strip() for item in value if str(item).strip()]
    else:
        lines = []
    return lines or list(fallback)


def _format_section(title: str, lines: list[str]) -> str:
    return f"{title}:\n" + "\n".join(f"- {line}" for line in lines) + "\n"


def _build_shared_instructions(project_id: str, audience: str) -> str:
    assistant_config = project_manager.get_assistant_config()
    llm_config = project_manager.get_llm_config(project_id)
    system_role = assistant_config.get(
        "system_role",
        "You are a Help Centre assistant. Use the project knowledge base as evidence and answer in a clear, task-oriented way.",
    )
    project_role = llm_config.get(
        "system_role",
        "You are a careful medical assistant. Use the provided project knowledge base as the primary source and answer with clear, safe, clinically grounded language.",
    )
    response_policy = _coerce_lines(assistant_config.get("response_policy"), DEFAULT_RESPONSE_POLICY)
    answer_style = _coerce_lines(assistant_config.get("answer_style"), DEFAULT_ANSWER_STYLE)
    question_types = _coerce_lines(assistant_config.get("question_types"), DEFAULT_QUESTION_TYPES)
    prompt_rules = project_manager.get_prompt_rules(project_id)

    audience_guidance = (
        [
            "Use simple, direct language that a non-specialist can follow.",
            "Explain jargon when it appears.",
        ]
        if audience == "general"
        else [
            "Use precise clinical language.",
            "Keep workflows, regimens, and terminology exact when the source is explicit.",
        ]
    )

    prompt = (
        f"System role:\n- {system_role}\n"
        f"Project role:\n- {project_role}\n"
        f"Project: {project_id}\n"
        f"Audience: {audience}\n"
        f"Answer strategy:\n"
        "- Read the question type and answer it in the most useful form for that type.\n"
        "- If the question is a procedure or workflow, provide steps rather than a document summary.\n"
        "- If the question is a definition or explanation, give the direct answer first, then brief context if needed.\n"
        "- If the question is incomplete or ambiguous, ask one clarifying question instead of guessing.\n"
        + _format_section("Response policy", response_policy)
        + _format_section("Answer style", answer_style)
        + _format_section("Question types", question_types)
        + _format_section("Audience guidance", audience_guidance)
        + (
            ""
            if not prompt_rules
            else _format_section("Project-specific rules", prompt_rules)
        )
        + "Use only the provided information and the current conversation when it is relevant.\n"
        + "Do not include raw markdown citations, raw URLs, or bracketed source references in the answer body.\n"
        + "If the retrieved information is incomplete, say what is known and clearly note the limitation.\n"
    )
    return prompt


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
