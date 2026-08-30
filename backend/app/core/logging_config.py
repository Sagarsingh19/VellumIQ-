import logging
import json
import time
from typing import Any, Dict

class JSONFormatter(logging.Formatter):
    """Structured JSON log formatter for production observability."""

    def format(self, record: logging.LogRecord) -> str:
        log_object: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        if record.exc_info:
            log_object["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_object)

def setup_logging():
    """Configures root logger to use JSON formatting."""
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers = [handler]
