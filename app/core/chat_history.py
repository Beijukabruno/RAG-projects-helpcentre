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
