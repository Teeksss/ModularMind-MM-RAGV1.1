"""
ModularMind platformu için kapsamlı loglama yapılandırması.
"""

import os
import sys
import logging
import logging.config
import json
from datetime import datetime
from pathlib import Path

def setup_logging():
    """
    Loglama sistemini yapılandırır.
    Logs dizinini oluşturur ve log seviyesine göre formatları ayarlar.
    """
    # Logs dizini oluştur
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Ortam ve log seviyesi
    environment = os.getenv("ENVIRONMENT", "development")
    log_level = os.getenv("LOG_LEVEL", "INFO")
    
    # JSON formatlı loglama için formatter
    class JsonFormatter(logging.Formatter):
        def format(self, record):
            log_record = {
                "timestamp": datetime.utcnow().isoformat(),
                "level": record.levelname,
                "message": record.getMessage(),
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno,
            }
            
            # Ekstra alanları ekle
            if hasattr(record, "request_id"):
                log_record["request_id"] = record.request_id
                
            if hasattr(record, "user_id"):
                log_record["user_id"] = record.user_id
                
            # Hata bilgilerini ekle
            if record.exc_info:
                log_record["exception"] = {
                    "type": record.exc_info[0].__name__,
                    "message": str(record.exc_info[1]),
                }
            
            return json.dumps(log_record)
    
    # Loglama yapılandırması
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: %(message)s"
            },
            "detailed": {
                "format": "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d [%(module)s.%(funcName)s]: %(message)s"
            },
            "json": {
                "()": JsonFormatter
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "DEBUG",
                "formatter": "standard",
                "stream": "ext://sys.stdout"
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": log_level,
                "formatter": "detailed",
                "filename": f"logs/modularmind_{environment}.log",
                "maxBytes": 10485760,  # 10 MB
                "backupCount": 5,
                "encoding": "utf8"
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "detailed",
                "filename": f"logs/error_{environment}.log",
                "maxBytes": 10485760,  # 10 MB
                "backupCount": 5,
                "encoding": "utf8"
            },
            "json_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": log_level,
                "formatter": "json",
                "filename": f"logs/modularmind_{environment}.json",
                "maxBytes": 10485760,  # 10 MB
                "backupCount": 5,
                "encoding": "utf8"
            }
        },
        "loggers": {
            "": {  # Root logger
                "handlers": ["console", "file", "error_file", "json_file"],
                "level": log_level,
                "propagate": True
            },
            "uvicorn": {
                "handlers": ["console", "file"],
                "level": log_level,
                "propagate": False
            },
            "uvicorn.access": {
                "handlers": ["console", "file"],
                "level": log_level,
                "propagate": False
            },
            "sqlalchemy.engine": {
                "handlers": ["console", "file"],
                "level": logging.WARNING,
                "propagate": False
            }
        }
    }
    
    # Logging yapılandırmasını uygula
    logging.config.dictConfig(logging_config)
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging system initialized: environment={environment}, level={log_level}")

# Request Context'i için filter
class RequestContextFilter(logging.Filter):
    """
    Log kayıtlarına request_id ve user_id ekleyen filtre.
    """
    
    def __init__(self, request_id=None, user_id=None):
        super().__init__()
        self.request_id = request_id
        self.user_id = user_id
    
    def filter(self, record):
        record.request_id = self.request_id
        record.user_id = self.user_id
        return True