from collections import defaultdict, deque
from datetime import datetime, timedelta

class ChatMemory:
    def __init__(self, max_messages=10, max_age_minutes=30):
        self.history = defaultdict(lambda: deque(maxlen=max_messages))
        self.max_age = timedelta(minutes=max_age_minutes)

    def add_message(self, user_id, role, content):
        """Store a new message with role and timestamp"""
        timestamp = datetime.utcnow()
        self.history[user_id].append({
            'role': role,
            'content': content,
            'timestamp': timestamp
        })

    def get_context(self, user_id):
        """Return recent message history within max_age"""
        now = datetime.utcnow()
        context = [
            (msg['role'], msg['content'])
            for msg in self.history[user_id]
            if now - msg['timestamp'] <= self.max_age
        ]
        return context

    def clear_context(self, user_id):
        """Wipe message history for a user"""
        self.history[user_id].clear()
