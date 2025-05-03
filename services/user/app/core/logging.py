import logging
import sys
import json
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Dict, Any

from app.core.config import settings

class JsonFormatter(logging.Formatter):
    """JSON log formatter."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_record: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "service": "user-service",
        }
        
        if hasattr(record, "request_id"):
            log_record["request_id"] = record.request_id
            
        if record.exc_info:
            exception_info = {
                "exception_type": record.exc_info[0].__name__,
                "exception_message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }
            log_record["exception"] = exception_info
            
        return json.dumps(log_record)

def setup_logging() -> None:
    """Setup logging for the application."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper())
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear existing handlers
    if root_logger.handlers:
        for handler in root_logger.handlers:
            root_logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(JsonFormatter())
    
    root_logger.addHandler(console_handler)
    
    # File handler if not in development
    if settings.ENVIRONMENT != "development":
        file_handler = RotatingFileHandler(
            "logs/user-service.log",
            maxBytes=10485760,  # 10MB
            backupCount=10
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(JsonFormatter())
        root_logger.addHandler(file_handler)
    
    # Reduce verbosity of some loggers
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    
    logging.info(f"Logging configured with level: {settings.LOG_LEVEL}")