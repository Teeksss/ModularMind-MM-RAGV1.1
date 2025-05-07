import os
from typing import List, Optional, Union, Dict, Any
from pydantic import BaseSettings, Field, validator

class Settings(BaseSettings):
    """Application settings."""
    
    # App configuration
    app_name: str = "ModularMind MM-RAG"
    app_description: str = "Modular Retrieval Augmented Generation API"
    version: str = "1.1.0"
    environment: str = Field("development", env="ENVIRONMENT")
    host: str = Field("0.0.0.0", env="HOST")
    port: int = Field(8000, env="PORT")
    
    # Security
    secret_key: str = Field("your-secret-key-here", env="SECRET_KEY")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 hours
    
    # MongoDB
    mongodb_url: str = Field("mongodb://localhost:27017", env="MONGODB_URL")
    mongodb_db_name: str = Field("modularmind", env="MONGODB_DB_NAME")
    
    # Redis
    redis_url: Optional[str] = Field(None, env="REDIS_URL")
    
    # CORS
    cors_origins: List[str] = ["*"]
    
    # Storage
    storage_type: str = Field("local", env="STORAGE_TYPE")  # local, s3, azure, gcp
    storage_path: str = Field("./data/files", env="STORAGE_PATH")
    
    # S3 Storage
    s3_bucket_name: Optional[str] = Field(None, env="S3_BUCKET_NAME")
    aws_access_key_id: Optional[str] = Field(None, env="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = Field(None, env="AWS_SECRET_ACCESS_KEY")
    aws_region: Optional[str] = Field(None, env="AWS_REGION")
    s3_endpoint_url: Optional[str] = Field(None, env="S3_ENDPOINT_URL")
    
    # Azure Storage
    azure_storage_connection_string: Optional[str] = Field(None, env="AZURE_STORAGE_CONNECTION_STRING")
    azure_container_name: Optional[str] = Field(None, env="AZURE_CONTAINER_NAME")
    
    # Model configuration
    default_model: str = Field("all-MiniLM-L6-v2", env="DEFAULT_MODEL")
    models_config_path: str = Field("./config/embedding_models.yaml", env="MODELS_CONFIG_PATH")
    multimodal_models_config_path: str = Field("./config/multimodal_models.yaml", env="MULTIMODAL_MODELS_CONFIG_PATH")
    
    # LLM configuration
    llm_service_type: str = Field("openai", env="LLM_SERVICE_TYPE")  # openai, local, etc.
    llm_model: str = Field("gpt-3.5-turbo", env="LLM_MODEL")
    openai_api_key: Optional[str] = Field(None, env="OPENAI_API_KEY")
    
    # Vector store
    vector_store_path: str = Field("./data/vector_indexes", env="VECTOR_STORE_PATH")
    
    # Fine-tuning
    fine_tuning_min_examples: int = Field(50, env="FINE_TUNING_MIN_EXAMPLES")
    
    # Rate limiting
    rate_limit_enabled: bool = Field(True, env="RATE_LIMIT_ENABLED")
    global_rate_limit: int = Field(100, env="GLOBAL_RATE_LIMIT")  # requests per minute
    
    # Logging
    log_level: str = Field("INFO", env="LOG_LEVEL")
    
    @validator("cors_origins", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Create settings instance
settings = Settings()