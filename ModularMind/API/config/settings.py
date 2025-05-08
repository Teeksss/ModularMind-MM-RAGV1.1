"""
Application settings validation using Pydantic
"""
from typing import List, Dict, Any, Optional, Union, Set
from pydantic import BaseSettings, validator, Field, AnyHttpUrl, PostgresDsn, RedisDsn
import os
from functools import lru_cache

class Settings(BaseSettings):
    """Application settings with validation"""
    
    # Application settings
    APP_NAME: str = "ModularMind RAG Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # Database settings
    DATABASE_URL: PostgresDsn
    
    # Redis settings
    REDIS_URL: RedisDsn
    
    # JWT settings
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_DELTA: int = 60 * 24  # 1 day in minutes
    
    # CORS settings
    CORS_ORIGINS: List[str] = ["*"]
    
    # API Key settings
    OPENAI_API_KEY: Optional[str] = None
    HUGGINGFACE_API_KEY: Optional[str] = None
    
    # Vector DB settings
    VECTOR_DB_TYPE: str = "faiss"
    VECTOR_DB_URL: Optional[str] = None
    VECTOR_DB_API_KEY: Optional[str] = None
    
    # Logging settings
    LOG_LEVEL: str = "info"
    
    # Model settings
    MODEL_CACHE_DIR: Optional[str] = None
    
    # Rate limiting settings
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT: int = 100  # requests per minute
    RATE_LIMIT_WINDOW: int = 60  # window size in seconds
    
    # Background task settings
    BACKGROUND_TASK_ENABLED: bool = True
    MAX_BACKGROUND_TASKS: int = 10
    
    # File upload settings
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB
    
    # Celery settings
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None
    
    # Base directory for the project
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    @validator("CORS_ORIGINS")
    def validate_cors_origins(cls, v):
        """Validate CORS origins"""
        if v and v[0] != "*":
            parsed = []
            for origin in v:
                # Ensure each origin is properly formatted
                if origin != "*":
                    # Add scheme if not present
                    if not origin.startswith(("http://", "https://")):
                        origin = f"https://{origin}"
                parsed.append(origin)
            return parsed
        return v
    
    @validator("LOG_LEVEL")
    def validate_log_level(cls, v):
        """Validate log level"""
        valid_levels = ["debug", "info", "warning", "error", "critical"]
        if v.lower() not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_levels}")
        return v.lower()
    
    @validator("VECTOR_DB_TYPE")
    def validate_vector_db_type(cls, v):
        """Validate vector DB type"""
        valid_types = ["faiss", "pinecone", "qdrant", "weaviate", "milvus"]
        if v.lower() not in valid_types:
            raise ValueError(f"VECTOR_DB_TYPE must be one of {valid_types}")
        return v.lower()
    
    @validator("UPLOAD_DIR")
    def validate_upload_dir(cls, v, values):
        """Ensure upload directory exists"""
        full_path = os.path.join(values.get("BASE_DIR", "."), v)
        os.makedirs(full_path, exist_ok=True)
        return v
    
    class Config:
        """Pydantic config"""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    Create and cache settings
    
    Returns:
        Settings: Application settings
    """
    return Settings()