"""
ModularMind platformu için yapılandırma modülü.
Ortam değişkenleri, yapılandırma dosyaları ve varsayılan değerler burada yönetilir.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Union, Type, TypeVar, cast
from pydantic import BaseModel, Field, validator

# Ortam değişkeni isimleri için sabitler
ENV_PREFIX = "MODULARMIND_"
ENV_CONFIG_FILE = f"{ENV_PREFIX}CONFIG_FILE"
ENV_ENVIRONMENT = f"{ENV_PREFIX}ENVIRONMENT"

# Yapılandırma türleri
T = TypeVar('T', bound=BaseModel)

class LoggingConfig(BaseModel):
    """Loglama yapılandırması."""
    level: str = "INFO"
    format: str = "standard"  # standard, json, detailed
    log_to_file: bool = True
    log_to_console: bool = True
    log_dir: str = "logs"
    log_max_size_mb: int = 10
    log_backup_count: int = 5
    request_log_format: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    @validator('level')
    def validate_level(cls, v):
        """Log seviyesinin geçerli olduğunu doğrula."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f"Log seviyesi geçerli değil. Geçerli seçenekler: {valid_levels}")
        return v.upper()

class DatabaseConfig(BaseModel):
    """Veritabanı yapılandırması."""
    uri: str = "mongodb://localhost:27017/modularmind"
    max_pool_size: int = 100
    min_pool_size: int = 10
    connect_timeout_ms: int = 5000
    socket_timeout_ms: int = 30000
    server_selection_timeout_ms: int = 30000
    replica_set: Optional[str] = None
    auto_retry_writes: bool = True
    retries: int = 3
    
    @validator('uri')
    def validate_uri(cls, v):
        """URI'nin MongoDB bağlantı dizgesi olduğunu doğrula."""
        if not v.startswith(('mongodb://', 'mongodb+srv://')):
            raise ValueError("Veritabanı URI'si 'mongodb://' veya 'mongodb+srv://' ile başlamalıdır")
        return v

class RedisConfig(BaseModel):
    """Redis yapılandırması."""
    uri: str = "redis://localhost:6379/0"
    pool_size: int = 100
    socket_timeout: int = 5
    socket_connect_timeout: int = 5
    connection_timeout: int = 5
    retry_on_timeout: bool = True
    max_retries: int = 3

class LLMConfig(BaseModel):
    """LLM servis yapılandırması."""
    provider: str = "openai"  # openai, azure, huggingface, anthropic, etc.
    api_key: str = ""
    api_base: Optional[str] = None
    model: str = "gpt-3.5-turbo"
    timeout: int = 60
    default_temperature: float = 0.7
    default_max_tokens: int = 1000
    system_prompt: str = "You are a helpful assistant."
    retry_count: int = 3
    retry_delay: int = 2
    max_concurrent_requests: int = 10
    requests_per_minute: int = 100
    cost_tracking: bool = True
    fallback_models: List[str] = []

class VectorDBConfig(BaseModel):
    """Vektör veritabanı yapılandırması."""
    provider: str = "chroma"  # chroma, pinecone, qdrant, weaviate, etc.
    api_key: Optional[str] = None
    url: Optional[str] = None
    collection_name: str = "documents"
    embedding_model: str = "text-embedding-3-large"
    embedding_dimension: int = 1536
    similarity_metric: str = "cosine"
    persist_directory: str = "vectorstore"
    search_k: int = 10
    reranking_enabled: bool = True
    reranking_model: Optional[str] = None

class CORSConfig(BaseModel):
    """CORS yapılandırması."""
    allow_origins: List[str] = ["*"]
    allow_credentials: bool = True
    allow_methods: List[str] = ["*"]
    allow_headers: List[str] = ["*"]
    max_age: int = 600

class CacheConfig(BaseModel):
    """Önbellek yapılandırması."""
    strategy: str = "tiered"  # none, simple, tiered, sharded
    redis_enabled: bool = True
    default_ttl: int = 3600
    memory_cache_size: int = 10000
    use_cache_middleware: bool = True
    cache_api_responses: bool = True
    exclude_paths: List[str] = ["/api/v1/auth", "/api/v2/auth", "/metrics", "/health"]

class AuthConfig(BaseModel):
    """Kimlik doğrulama yapılandırması."""
    jwt_secret_key: str = "change_this_secret_key_in_production"
    token_expire_minutes: int = 60 * 24  # 1 day
    refresh_token_expire_days: int = 7
    password_min_length: int = 8
    password_require_uppercase: bool = True
    password_require_lowercase: bool = True
    password_require_digits: bool = True
    password_require_special: bool = True
    max_login_attempts: int = 5
    lockout_minutes: int = 15
    allow_basic_auth: bool = False
    allow_api_key: bool = True
    
    @validator('jwt_secret_key')
    def validate_jwt_secret(cls, v, values, **kwargs):
        """JWT anahtarının üretim ortamında güçlü olduğunu doğrula."""
        if os.getenv(f"{ENV_PREFIX}ENVIRONMENT", "").lower() == "production":
            if v == "change_this_secret_key_in_production" or len(v) < 32:
                raise ValueError("Üretim ortamında güçlü bir JWT anahtarı kullanmalısınız")
        return v

class RateLimitConfig(BaseModel):
    """Rate limiting yapılandırması."""
    enabled: bool = True
    strategy: str = "fixed-window"  # fixed-window, sliding-window, token-bucket
    redis_enabled: bool = True
    default_rate: int = 100
    default_period: int = 60
    auth_rate: int = 20
    auth_period: int = 60
    exclude_paths: List[str] = ["/health", "/metrics"]
    include_headers: bool = True
    by_ip: bool = True
    by_user: bool = True

class MultimodalConfig(BaseModel):
    """Multimodal yapılandırması."""
    enabled: bool = True
    image_processor: str = "openai"  # openai, clip, etc.
    video_processor: str = "ffmpeg"
    audio_processor: str = "whisper"
    max_image_size_mb: int = 10
    max_video_size_mb: int = 50
    max_audio_size_mb: int = 25
    supported_image_formats: List[str] = ["jpg", "jpeg", "png", "gif", "webp"]
    supported_video_formats: List[str] = ["mp4", "avi", "mov", "mkv", "webm"]
    supported_audio_formats: List[str] = ["mp3", "wav", "ogg", "m4a", "flac"]
    storage_path: str = "multimodal_data"

class FineTuningConfig(BaseModel):
    """Fine-tuning yapılandırması."""
    enabled: bool = True
    provider: str = "openai"  # openai, huggingface, etc.
    max_jobs_per_user: int = 5
    max_concurrent_jobs: int = 3
    max_dataset_size_mb: int = 100
    dataset_storage_path: str = "finetune_data"
    model_storage_path: str = "finetune_models"
    supported_formats: List[str] = ["jsonl", "csv", "txt"]
    timeout_hours: int = 24

class AppConfig(BaseModel):
    """Ana uygulama yapılandırması."""
    app_name: str = "ModularMind API"
    app_version: str = "1.2.0"
    environment: str = "development"
    debug: bool = False
    api_prefix: str = "/api"
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 4
    reload: bool = False
    root_path: str = ""
    docs_url: str = "/docs"
    redoc_url: str = "/redoc"
    openapi_url: str = "/openapi.json"
    static_directory: str = "static"
    upload_directory: str = "uploads"
    temp_directory: str = "temp"
    max_upload_size_mb: int = 50
    log_requests: bool = True
    log_responses: bool = False
    timezone: str = "UTC"
    
    # Alt yapılandırmalar
    logging: LoggingConfig = LoggingConfig()
    database: DatabaseConfig = DatabaseConfig()
    redis: RedisConfig = RedisConfig()
    llm: LLMConfig = LLMConfig()
    vector_db: VectorDBConfig = VectorDBConfig()
    cors: CORSConfig = CORSConfig()
    cache: CacheConfig = CacheConfig()
    auth: AuthConfig = AuthConfig()
    rate_limit: RateLimitConfig = RateLimitConfig()
    multimodal: MultimodalConfig = MultimodalConfig()
    fine_tuning: FineTuningConfig = FineTuningConfig()

def load_config_from_file(file_path: str) -> Dict[str, Any]:
    """
    Belirtilen dosyadan yapılandırma yükler.
    
    Args:
        file_path: Yapılandırma dosyası yolu
        
    Returns:
        Dict[str, Any]: Yapılandırma sözlüğü
    """
    try:
        with open(file_path, 'r') as f:
            if file_path.endswith('.json'):
                return json.load(f)
            else:
                raise ValueError(f"Desteklenmeyen yapılandırma dosyası formatı: {file_path}")
    except Exception as e:
        logging.warning(f"Yapılandırma dosyası yüklenemedi: {file_path}, Hata: {str(e)}")
        return {}

def load_config_from_env() -> Dict[str, Any]:
    """
    Ortam değişkenlerinden yapılandırma yükler.
    
    Returns:
        Dict[str, Any]: Yapılandırma sözlüğü
    """
    config_dict = {}
    
    for env_var, value in os.environ.items():
        if env_var.startswith(ENV_PREFIX) and env_var not in [ENV_CONFIG_FILE, ENV_ENVIRONMENT]:
            # Ortam değişkeni ismini yapılandırma anahtarına dönüştür
            # MODULARMIND_APP_NAME -> app_name
            # MODULARMIND_DATABASE_URI -> database.uri
            key = env_var[len(ENV_PREFIX):].lower()
            key_parts = key.split('_')
            
            # Alt yapılandırma anahtarlarını belirle
            if len(key_parts) > 1 and key_parts[0] in [
                'logging', 'database', 'redis', 'llm', 'vector_db', 'cors',
                'cache', 'auth', 'rate_limit', 'multimodal', 'fine_tuning'
            ]:
                config_section = key_parts[0]
                config_key = '_'.join(key_parts[1:])
                
                if config_section not in config_dict:
                    config_dict[config_section] = {}
                
                config_dict[config_section][config_key] = value
            else:
                config_dict[key] = value
    
    # Değerleri doğru tiplere dönüştür
    return config_dict

def get_config() -> AppConfig:
    """
    Uygulama yapılandırmasını yükleyip döndürür.
    
    Returns:
        AppConfig: Uygulama yapılandırma nesnesi
    """
    config_dict = {}
    
    # 1. Varsayılan yapılandırma
    config_dict = AppConfig().dict()
    
    # 2. Dosya tabanlı yapılandırma (varsa)
    config_file = os.getenv(ENV_CONFIG_FILE)
    if config_file and os.path.exists(config_file):
        file_config = load_config_from_file(config_file)
        config_dict = deep_update(config_dict, file_config)
    
    # 3. Ortam değişkenleri tabanlı yapılandırma
    env_config = load_config_from_env()
    config_dict = deep_update(config_dict, env_config)
    
    # 4. Ortam değişkeninden direkt olarak environment değerini al
    environment = os.getenv(ENV_ENVIRONMENT)
    if environment:
        config_dict['environment'] = environment
    
    # 5. Kritik bilgiler için ortam değişkenlerini doğrudan kontrol et
    # API anahtarları gibi hassas veriler için öncelikle ortam değişkenlerini kullan
    api_key_env_vars = {
        'OPENAI_API_KEY': ('llm', 'api_key'),
        'PINECONE_API_KEY': ('vector_db', 'api_key'),
        'JWT_SECRET_KEY': ('auth', 'jwt_secret_key'),
    }
    
    for env_var, (section, key) in api_key_env_vars.items():
        value = os.getenv(env_var)
        if value:
            if section not in config_dict:
                config_dict[section] = {}
            config_dict[section][key] = value
    
    # Pydantic modeli ile doğrula ve döndür
    return AppConfig(**config_dict)

def deep_update(original: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
    """
    İç içe geçmiş sözlükleri derin bir şekilde günceller.
    
    Args:
        original: Orijinal sözlük
        update: Güncelleme sözlüğü
        
    Returns:
        Dict[str, Any]: Güncellenmiş sözlük
    """
    result = original.copy()
    
    for key, value in update.items():
        if isinstance(value, dict) and key in result and isinstance(result[key], dict):
            result[key] = deep_update(result[key], value)
        else:
            result[key] = value
    
    return result

# Global yapılandırma nesnesi
try:
    config = get_config()
except Exception as e:
    logging.error(f"Yapılandırma yüklenemedi: {str(e)}")
    # Varsayılan yapılandırma ile devam et
    config = AppConfig()