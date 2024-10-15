import logging
from logging.handlers import RotatingFileHandler
import json
from datetime import datetime
from flask import request

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        for attr in ['session_id', 'ip_address', 'user_agent', 'user_message', 'bot_message']:
            if hasattr(record, attr):
                log_record[attr] = getattr(record, attr)
        return json.dumps(log_record)

def setup_logger(log_file='app.log', max_bytes=10000, backup_count=3):
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    handler = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count)
    handler.setFormatter(JSONFormatter())

    logger.addHandler(handler)
    return logger

logger = setup_logger()

def log_session(session_id):
    ip_address = request.remote_addr
    user_agent = request.user_agent.string

    logger.info("New session started", extra={
        'session_id': session_id,
        'ip_address': ip_address,
        'user_agent': user_agent
    })

def log_interaction(session_id, user_message, bot_message):
    logger.info("Q&A interaction", extra={
        'session_id': session_id,
        'user_message': user_message,
        'bot_message': bot_message
    })
