from collections import defaultdict


class Message:
    def __init__(self, message_type: str, content: str):
        self.type = message_type
        self.content = content


class InMemoryChatMessageHistory:
    def __init__(self):
        self.messages = []

    def add_user_message(self, content: str) -> None:
        self.messages.append(Message("human", content))

    def add_ai_message(self, content: str) -> None:
        self.messages.append(Message("ai", content))


class SessionChatHistoryStore:
    """Keep separate histories per session key to avoid cross-user leakage."""

    def __init__(self):
        self._store = defaultdict(InMemoryChatMessageHistory)

    def get(self, session_key: str) -> InMemoryChatMessageHistory:
        return self._store[session_key]
