from typing import List, Set, Dict, Optional, Any, Union
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings
import yaml
import os
import json


# Configuration Models
class ServerSettings(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    environment: str = "production"
    debug: bool = False
    log_level: str = "INFO"


class SecuritySettings(BaseModel):
    secret_key: str
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30
    password_min_length: int = 8
    cors_origins: List[str] = ["*"]


class DatabaseSettings(BaseModel):
    db_url: str
    max_connections: int = 10
    min_connections: int = 1
    echo: bool = False


class RedisSettings(BaseModel):
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: Optional[str] = None
    redis_db: int = 0


class VectorStoreSettings(BaseModel):
    vector_db_type: str = "qdrant"  # qdrant, faiss, milvus
    vector_db_url: str = "http://localhost:6333"
    vector_db_api_key: Optional[str] = None
    collection_name: str = "modularmind"
    vector_dimension: int = 1536
    similarity_type: str = "cosine"  # cosine, dot, euclidean


class LLMSettings(BaseModel):
    llm_provider: str = "openai"  # openai, mistral, anthropic, local
    llm_model: str = "gpt-4"
    llm_api_key: str
    local_llm_server: Optional[str] = None
    local_llm_model_id: Optional[str] = None
    temperature: float = 0.0
    max_tokens: int = 2048
    timeout: int = 30


class EmbeddingsSettings(BaseModel):
    embedding_model: str = "text-embedding-3-large"
    embedding_dimension: int = 1536
    use_cache: bool = True
    cache_ttl: int = 86400  # 1 day


class AgentSettings(BaseModel):
    agents_enabled: bool = True
    active_agents: List[str] = [
        "MetadataExtractorAgent",
        "SummarizationAgent",
        "SemanticExpanderAgent",
        "ContextualTaggerAgent",
        "RelationBuilderAgent",
        "SyntheticQAGeneratorAgent"
    ]
    timeout_seconds: int = 30
    retry_attempts: int = 3
    concurrency: int = 2


class EnrichmentSettings(BaseModel):
    enrichment_enabled: bool = True
    synthetic_qa_enabled: bool = True
    synthetic_qa_questions_per_document: int = 10
    synthetic_qa_diversity_factor: float = 0.3
    entity_masking_enabled: bool = False


class MultilingualSettings(BaseModel):
    default_language: str = "en"
    supported_languages: List[str] = ["en", "tr", "de", "fr"]
    translation_enabled: bool = False
    translation_model: Optional[str] = None


class RetrievalSettings(BaseModel):
    retrieval_type: str = "hybrid"  # dense, sparse, hybrid
    top_k: int = 5
    reranking_enabled: bool = False
    similarity_threshold: float = 0.7
    include_metadata: bool = True


class MemorySettings(BaseModel):
    memory_enabled: bool = True
    memory_max_history_items: int = 20
    memory_ttl_seconds: int = 86400 * 7  # 7 days


class MetricsSettings(BaseModel):
    metrics_enabled: bool = True
    log_request_body: bool = False
    log_response_body: bool = False
    prometheus_enabled: bool = True


class Settings(BaseSettings):
    server: ServerSettings = Field(default_factory=ServerSettings)
    security: SecuritySettings
    database: DatabaseSettings
    redis: RedisSettings = Field(default_factory=RedisSettings)
    vector_store: VectorStoreSettings = Field(default_factory=VectorStoreSettings)
    llm: LLMSettings
    embeddings: EmbeddingsSettings = Field(default_factory=EmbeddingsSettings)
    agents: AgentSettings = Field(default_factory=AgentSettings)
    enrichment: EnrichmentSettings = Field(default_factory=EnrichmentSettings)
    multilingual: MultilingualSettings = Field(default_factory=MultilingualSettings)
    retrieval: RetrievalSettings = Field(default_factory=RetrievalSettings)
    memory: MemorySettings = Field(default_factory=MemorySettings)
    metrics: MetricsSettings = Field(default_factory=MetricsSettings)
    
    class Config:
        env_file = ".env"
        env_nested_delimiter = "__"


def load_config_from_yaml(file_path: str = "config.yaml") -> Dict[str, Any]:
    """Load configuration from YAML file."""
    if not os.path.exists(file_path):
        return {}
    
    with open(file_path, "r") as f:
        return yaml.safe_load(f)


def load_config_from_env() -> Dict[str, Any]:
    """Load configuration from environment variables."""
    config = {}
    
    # Map environment variables to config structure
    env_mapping = {
        "SERVER__HOST": ("server", "host"),
        "SERVER__PORT": ("server", "port", int),
        "SERVER__ENVIRONMENT": ("server", "environment"),
        "SERVER__DEBUG": ("server", "debug", lambda x: x.lower() == "true"),
        "SERVER__LOG_LEVEL": ("server", "log_level"),
        
        "SECURITY__SECRET_KEY": ("security", "secret_key"),
        "SECURITY__ACCESS_TOKEN_EXPIRE_MINUTES": ("security", "access_token_expire_minutes", int),
        "SECURITY__REFRESH_TOKEN_EXPIRE_DAYS": ("security", "refresh_token_expire_days", int),
        "SECURITY__PASSWORD_MIN_LENGTH": ("security", "password_min_length", int),
        "SECURITY__CORS_ORIGINS": ("security", "cors_origins", lambda x: x.split(",")),
        
        "DATABASE_URL": ("database", "db_url"),
        "DATABASE__MAX_CONNECTIONS": ("database", "max_connections", int),
        "DATABASE__MIN_CONNECTIONS": ("database", "min_connections", int),
        "DATABASE__ECHO": ("database", "echo", lambda x: x.lower() == "true"),
        
        "REDIS__REDIS_HOST": ("redis", "redis_host"),
        "REDIS__REDIS_PORT": ("redis", "redis_port", int),
        "REDIS__REDIS_PASSWORD": ("redis", "redis_password"),
        "REDIS__REDIS_DB": ("redis", "redis_db", int),
        
        "VECTOR_STORE__VECTOR_DB_TYPE": ("vector_store", "vector_db_type"),
        "VECTOR_STORE__VECTOR_DB_URL": ("vector_store", "vector_db_url"),
        "VECTOR_STORE__VECTOR_DB_API_KEY": ("vector_store", "vector_db_api_key"),
        "VECTOR_STORE__COLLECTION_NAME": ("vector_store", "collection_name"),
        "VECTOR_STORE__VECTOR_DIMENSION": ("vector_store", "vector_dimension", int),
        "VECTOR_STORE__SIMILARITY_TYPE": ("vector_store", "similarity_type"),
        
        "LLM__LLM_PROVIDER": ("llm", "llm_provider"),
        "LLM__LLM_MODEL": ("llm", "llm_model"),
        "LLM__LLM_API_KEY": ("llm", "llm_api_key"),
        "LLM__LOCAL_LLM_SERVER": ("llm", "local_llm_server"),
        "LLM__LOCAL_LLM_MODEL_ID": ("llm", "local_llm_model_id"),
        "LLM__TEMPERATURE": ("llm", "temperature", float),
        "LLM__MAX_TOKENS": ("llm", "max_tokens", int),
        "LLM__TIMEOUT": ("llm", "timeout", int),
        
        "EMBEDDINGS__EMBEDDING_MODEL": ("embeddings", "embedding_model"),
        "EMBEDDINGS__EMBEDDING_DIMENSION": ("embeddings", "embedding_dimension", int),
        "EMBEDDINGS__USE_CACHE": ("embeddings", "use_cache", lambda x: x.lower() == "true"),
        "EMBEDDINGS__CACHE_TTL": ("embeddings", "cache_ttl", int),
        
        "AGENTS__AGENTS_ENABLED": ("agents", "agents_enabled", lambda x: x.lower() == "true"),
        "AGENTS__ACTIVE_AGENTS": ("agents", "active_agents", lambda x: json.loads(x)),
        "AGENTS__TIMEOUT_SECONDS": ("agents", "timeout_seconds", int),
        "AGENTS__RETRY_ATTEMPTS": ("agents", "retry_attempts", int),
        "AGENTS__CONCURRENCY": ("agents", "concurrency", int),
        
        "ENRICHMENT__ENABLED": ("enrichment", "enrichment_enabled", lambda x: x.lower() == "true"),
        "ENRICHMENT__SYNTHETIC_QA__ENABLED": ("enrichment", "synthetic_qa_enabled", lambda x: x.lower() == "true"),
        "ENRICHMENT__SYNTHETIC_QA__QUESTIONS_PER_DOCUMENT": ("enrichment", "synthetic_qa_questions_per_document", int),
        "ENRICHMENT__SYNTHETIC_QA__DIVERSITY_FACTOR": ("enrichment", "synthetic_qa_diversity_factor", float),
        "ENRICHMENT__ENTITY_MASKING__ENABLED": ("enrichment", "entity_masking_enabled", lambda x: x.lower() == "true"),
        
        "MULTILINGUAL__DEFAULT_LANGUAGE": ("multilingual", "default_language"),
        "MULTILINGUAL__SUPPORTED_LANGUAGES": ("multilingual", "supported_languages", lambda x: json.loads(x)),
        "MULTILINGUAL__TRANSLATION_ENABLED": ("multilingual", "translation_enabled", lambda x: x.lower() == "true"),
        "MULTILINGUAL__TRANSLATION_MODEL": ("multilingual", "translation_model"),
        
        "RETRIEVAL__RETRIEVAL_TYPE": ("retrieval", "retrieval_type"),
        "RETRIEVAL__TOP_K": ("retrieval", "top_k", int),
        "RETRIEVAL__RERANKING_ENABLED": ("retrieval", "reranking_enabled", lambda x: x.lower() == "true"),
        "RETRIEVAL__SIMILARITY_THRESHOLD": ("retrieval", "similarity_threshold", float),
        "RETRIEVAL__INCLUDE_METADATA": ("retrieval", "include_metadata", lambda x: x.lower() == "true"),
        
        "MEMORY__ENABLED": ("memory", "memory_enabled", lambda x: x.lower() == "true"),
        "MEMORY__MAX_HISTORY_ITEMS": ("memory", "memory_max_history_items", int),
        "MEMORY__TTL_SECONDS": ("memory", "memory_ttl_seconds", int),
        
        "METRICS__ENABLED": ("metrics", "metrics_enabled", lambda x: x.lower() == "true"),
        "METRICS__LOG_REQUEST_BODY": ("metrics", "log_request_body", lambda x: x.lower() == "true"),
        "METRICS__LOG_RESPONSE_BODY": ("metrics", "log_response_body", lambda x: x.lower() == "true"),
        "METRICS__PROMETHEUS_ENABLED": ("metrics", "prometheus_enabled", lambda x: x.lower() == "true"),
    }
    
    for env_var, config_path in env_mapping.items():
        env_value = os.environ.get(env_var)
        
        if env_value is not None:
            # Get path and converter if available
            if len(config_path) == 3:
                section, key, converter = config_path
            else:
                section, key = config_path
                converter = lambda x: x  # Identity function
            
            # Initialize section if it doesn't exist
            if section not in config:
                config[section] = {}
            
            # Convert and store value
            try:
                config[section][key] = converter(env_value)
            except Exception as e:
                print(f"Error converting {env_var}: {e}")
    
    return config


def get_settings() -> Settings:
    """Get application settings from multiple sources."""
    # Load configuration from YAML
    yaml_config = load_config_from_yaml()
    
    # Load configuration from environment variables
    env_config = load_config_from_env()
    
    # Merge configurations (environment variables take precedence)
    merged_config = {}
    
    # Add YAML config
    for section, values in yaml_config.items():
        merged_config[section] = values
    
    # Add/override with environment config
    for section, values in env_config.items():
        if section in merged_config:
            merged_config[section].update(values)
        else:
            merged_config[section] = values
    
    # Create Settings object
    return Settings(**merged_config)