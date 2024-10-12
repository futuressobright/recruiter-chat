# timing_utils.py

import time
import logging
from functools import wraps

logger = logging.getLogger(__name__)

def timed_operation(operation_name):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            logger.info(f"{operation_name} took {end_time - start_time:.2f} seconds")
            return result
        return wrapper
    return decorator
