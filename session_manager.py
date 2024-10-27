import random
import string
from logger import log_session

class SessionManager:
    """Manages chat sessions and their message histories"""
    
    def __init__(self, employer_name):
        self.sessions = {}
        self.employer_name = employer_name

    def generate_unique_id(self):
        while True:
            random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
            random_integer = random.randint(1000, 9999)
            unique_id = f"{self.employer_name}-{random_string}{random_integer}"
            if unique_id not in self.sessions:
                return unique_id

    def create_session(self):
        """Create a new session and return its ID"""
        session_id = self.generate_unique_id()
        self.sessions[session_id] = {"chat_history": []}
        log_session(session_id)
        return session_id

    def get_session(self, session_id):
        """Retrieve a session by its ID"""
        return self.sessions.get(session_id)

    def add_message(self, session_id, role, content):
        """Add a message to a session's chat history"""
        if session_id in self.sessions:
            self.sessions[session_id]['chat_history'].append({
                "role": role, 
                "content": content
            })

    def clear_history(self, session_id):
        """Clear the chat history for a session"""
        if session_id in self.sessions:
            self.sessions[session_id]['chat_history'] = []
