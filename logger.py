from logtail import LogtailHandler
import logging
import json
from datetime import datetime
from flask import request
from typing import Optional


class CustomLogFormatter(logging.Formatter):
    def format(self, record):
        # Preserve existing log structure
        log_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "environment": "production"  # You might want to make this configurable
        }

        # Add extra fields if they exist
        for attr in ['session_id', 'ip_address', 'user_agent', 'user_message', 'bot_message']:
            if hasattr(record, attr):
                log_record[attr] = getattr(record, attr)

        # Logtail expects a string
        return json.dumps(log_record)


def setup_logger(source_token: str) -> logging.Logger:
    """
    Set up the Logtail logger with the given source token.

    Args:
        source_token: The Logtail source token from your Logtail dashboard
    """
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    # Create Logtail handler
    handler = LogtailHandler(source_token=source_token)
    handler.setFormatter(CustomLogFormatter())

    # Remove any existing handlers and add Logtail handler
    logger.handlers.clear()
    logger.addHandler(handler)

    return logger


# Initialize logger with None - will be set up properly when configure_logging is called
logger: Optional[logging.Logger] = None


def configure_logging(source_token: str):
    """
    Configure the logger with your Logtail source token.
    Call this during application startup.
    """
    global logger
    logger = setup_logger(source_token)


def log_session(session_id: str):
    """Log new session creation"""
    if not logger:
        raise RuntimeError("Logger not configured. Call configure_logging first.")

    ip_address = request.remote_addr
    user_agent = request.user_agent.string

    logger.info("New session started", extra={
        'session_id': session_id,
        'ip_address': ip_address,
        'user_agent': user_agent
    })


def log_interaction(session_id: str, user_message: str, bot_message: str):
    """Log chat interaction"""
    if not logger:
        raise RuntimeError("Logger not configured. Call configure_logging first.")

    logger.info("Q&A interaction", extra={
        'session_id': session_id,
        'user_message': user_message,
        'bot_message': bot_message
    })