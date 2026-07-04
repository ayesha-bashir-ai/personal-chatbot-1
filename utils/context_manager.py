import os, json

class ContextManager:
    def __init__(self):
        self.history = []
        self.session_context = []

    def add_to_history(self, message):
        self.history.append(message)

    def add_to_context(self, event):
        self.session_context.append(event)

    def get_recent_context(self, n=10):
        return self.session_context[-n:]

    def get_conversation_context(self):
        return self.history

    def clear_session_context(self):
        self.session_context = []
