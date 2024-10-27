class ChatError(Exception):
    """Base exception class for chat application errors"""
    def __init__(self, message, status_code=500):
        super().__init__(message)
        self.status_code = status_code
        self.message = message

class SessionNotFoundError(ChatError):
    """Raised when a session ID is not found"""
    def __init__(self, session_id):
        super().__init__(f"Session not found: {session_id}", status_code=404)

class ConfigurationError(ChatError):
    """Raised when there's an error with configuration"""
    def __init__(self, message):
        super().__init__(f"Configuration error: {message}", status_code=500)
