#!/usr/bin/env python3
"""
ModularMind RAG Platform - Model İndirme Scripti
Bu script gerekli yerel modelleri indirir ve yapılandırır.
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
import shutil
import requests
from tqdm import tqdm
import yaml

# Logging yapılandırması
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("model-downloader")

# Sabit değişkenler
MODEL_DIR = Path("./models")
CONFIG_DIR = Path("./config")
EMBEDDING_CONFIG_FILE = CONFIG_DIR / "embedding_models.json"
LLM_CONFIG_FILE = CONFIG_DIR / "llm_models.json"
VECTOR_STORE_CONFIG_FILE = CONFIG_DIR / "vector_store.json"
MODEL_ROUTER_CONFIG_FILE = CONFIG_DIR / "model_router.json"

def create_dirs():
    """Gerekli dizinleri oluşturur."""
    MODEL_DIR.mkdir(exist_ok=True)
    (MODEL_DIR / "embeddings").mkdir(exist_ok=True)
    (MODEL_DIR / "llm").mkdir(exist_ok=True)
    CONFIG_DIR.mkdir(exist_ok=True)
    
    logger.info(f"Dizinler oluşturuldu: {MODEL_DIR}, {CONFIG_DIR}")

def download_huggingface_model(model_id, target_dir, force=False):
    """
    Hugging Face modelini indirir.
    
    Args:
        model_id: Hugging Face model ID
        target_dir: İndirme hedef dizini
        force: Varsa bile yeniden indir
    """
    from huggingface_hub import snapshot_download
    
    target_path = Path(target_dir) / model_id.split("/")[-1]
    
    if target_path.exists() and not force:
        logger.info(f"Model zaten mevcut: {target_path}")
        return target_path
    
    logger.info(f"İndiriliyor: {model_id}")
    
    try:
        path = snapshot_download(
            repo_id=model_id,
            local_dir=str(target_path),
            local_dir_use_symlinks=False
        )
        logger.info(f"Model indirildi: {path}")
        return target_path
    except Exception as e:
        logger.error(f"Model indirme hatası '{model_id}': {str(e)}")
        return None

def setup_embedding_models(args):
    """Embedding modellerini kurar."""
    
    default_embedding_models = [
        {
            "id": "all-MiniLM-L6-v2",
            "provider": "local",
            "model_id": "sentence-transformers/all-MiniLM-L6-v2",
            "name": "MiniLM L6 v2",
            "dimensions": 384
        },
        {
            "id": "text-embedding-3-small",
            "provider": "openai",
            "model_id": "text-embedding-3-small",
            "name": "OpenAI Embeddings Small",
            "dimensions": 1536,
            "api_key_env": "OPENAI_API_KEY"
        },
        {
            "id": "text-embedding-3-large",
            "provider": "openai",
            "model_id": "text-embedding-3-large",
            "name": "OpenAI Embeddings Large",
            "dimensions": 3072,
            "api_key_env": "OPENAI_API_KEY"
        }
    ]
    
    if args.add_multilingual:
        default_embedding_models.append({
            "id": "paraphrase-multilingual-MiniLM-L12-v2",
            "provider": "local",
            "model_id": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            "name": "Multilingual MiniLM L12 v2",
            "dimensions": 384
        })
    
    # Local modelleri indir
    for model in default_embedding_models:
        if model["provider"] == "local":
            download_huggingface_model(
                model["model_id"], 
                MODEL_DIR / "embeddings",
                force=args.force
            )
    
    # Embedding yapılandırmasını oluştur
    config = {
        "models": default_embedding_models,
        "default_model": "text-embedding-3-small"
    }
    
    # Yapılandırmayı kaydet
    with open(EMBEDDING_CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)
    
    logger.info(f"Embedding modelleri yapılandırması kaydedildi: {EMBEDDING_CONFIG_FILE}")

def setup_llm_models(args):
    """LLM modellerini kurar."""
    
    default_llm_models = [
        {
            "id": "gpt-4o",
            "provider": "openai",
            "model_id": "gpt-4o",
            "api_key_env": "OPENAI_API_KEY",
            "max_tokens": 4096,
            "temperature": 0.7
        },
        {
            "id": "gpt-3.5-turbo",
            "provider": "openai",
            "model_id": "gpt-3.5-turbo",
            "api_key_env": "OPENAI_API_KEY",
            "max_tokens": 4096,
            "temperature": 0.7
        }
    ]
    
    if args.add_anthropic:
        default_llm_models.append({
            "id": "claude-3-opus",
            "provider": "anthropic",
            "model_id": "claude-3-opus-20240229",
            "api_key_env": "ANTHROPIC_API_KEY",
            "max_tokens": 4096,
            "temperature": 0.7
        })
    
    if args.add_local_llm:
        # Yerel modeller için llama.cpp veya vLLM yapılandırması
        default_llm_models.append({
            "id": "local-llama",
            "provider": "local",
            "model_id": "local-server",
            "max_tokens": 2048,
            "temperature": 0.7,
            "api_base_url": "http://localhost:8080/v1"
        })
    
    # Yapılandırmayı kaydet
    config = {
        "models": default_llm_models
    }
    
    with open(LLM_CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)
    
    logger.info(f"LLM modelleri yapılandırması kaydedildi: {LLM_CONFIG_FILE}")

def setup_vector_store(args):
    """Vektör deposunu yapılandırır."""
    
    # Vektör deposu yapılandırması
    vector_store_config = {
        "index_type": "HNSW",
        "dimensions": {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "all-MiniLM-L6-v2": 384
        },
        "metric": "cosine",
        "storage_path": "./data/vector_store",
        "hnsw_params": {
            "M": 16,
            "ef_construction": 200,
            "ef_search": 50
        },
        "default_embedding_model": "text-embedding-3-small",
        "embedding_models": [
            "text-embedding-3-small",
            "text-embedding-3-large",
            "all-MiniLM-L6-v2"
        ]
    }
    
    if args.add_multilingual:
        vector_store_config["dimensions"]["paraphrase-multilingual-MiniLM-L12-v2"] = 384
        vector_store_config["embedding_models"].append("paraphrase-multilingual-MiniLM-L12-v2")
    
    # Yapılandırmayı kaydet
    with open(VECTOR_STORE_CONFIG_FILE, "w") as f:
        json.dump(vector_store_config, f, indent=2)
    
    logger.info(f"Vektör deposu yapılandırması kaydedildi: {VECTOR_STORE_CONFIG_FILE}")

def setup_model_router(args):
    """Model yönlendirici yapılandırır."""
    
    model_router_config = {
        "default_model_id": "text-embedding-3-small",
        "language_models": {
            "en": "text-embedding-3-small"
        },
        "domain_models": {
            "finance": "text-embedding-3-small",
            "legal": "text-embedding-3-large",
            "medical": "text-embedding-3-large",
            "tech": "all-MiniLM-L6-v2"
        },
        "fallback_model_id": "text-embedding-3-small",
        "enable_auto_routing": True,
        "enable_ensemble": True,
        "ensemble_method": "weighted_average",
        "result_aggregation": "weighted_average"
    }
    
    if args.add_multilingual:
        model_router_config["language_models"]["tr"] = "paraphrase-multilingual-MiniLM-L12-v2"
        model_router_config["language_models"]["es"] = "paraphrase-multilingual-MiniLM-L12-v2"
        model_router_config["language_models"]["de"] = "paraphrase-multilingual-MiniLM-L12-v2"
        model_router_config["language_models"]["fr"] = "paraphrase-multilingual-MiniLM-L12-v2"
    
    # Yapılandırmayı kaydet
    with open(MODEL_ROUTER_CONFIG_FILE, "w") as f:
        json.dump(model_router_config, f, indent=2)
    
    logger.info(f"Model yönlendirici yapılandırması kaydedildi: {MODEL_ROUTER_CONFIG_FILE}")

def generate_env(args):
    """
    .env dosyası oluşturur.
    """
    env_path = Path(".env")
    
    # Varsayılan çevre değişkenleri
    env_vars = {
        "LOG_LEVEL": "INFO",
        "API_TOKEN": args.api_token or "modularmind_default_token",
        "HOST": "0.0.0.0",
        "PORT": "8000"
    }
    
    # API anahtarları
    if args.openai_key:
        env_vars["OPENAI_API_KEY"] = args.openai_key
    
    if args.anthropic_key:
        env_vars["ANTHROPIC_API_KEY"] = args.anthropic_key
    
    if args.cohere_key:
        env_vars["COHERE_API_KEY"] = args.cohere_key
    
    if args.azure_openai_key:
        env_vars["AZURE_OPENAI_API_KEY"] = args.azure_openai_key
    
    # .env dosyası oluştur
    with open(env_path, "w") as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")
    
    logger.info(f".env dosyası oluşturuldu: {env_path}")

def main():
    """Ana işlevi çalıştırır."""
    parser = argparse.ArgumentParser(description="ModularMind Model İndirme ve Kurulum Aracı")
    
    parser.add_argument("--force", action="store_true", help="Var olan modelleri yeniden indir")
    parser.add_argument("--add-multilingual", action="store_true", help="Çok dilli modelleri dahil et")
    parser.add_argument("--add-anthropic", action="store_true", help="Anthropic modellerini dahil et")
    parser.add_argument("--add-local-llm", action="store_true", help="Yerel LLM yapılandırmasını dahil et")
    parser.add_argument("--openai-key", help="OpenAI API anahtarı")
    parser.add_argument("--anthropic-key", help="Anthropic API anahtarı")
    parser.add_argument("--cohere-key", help="Cohere API anahtarı")
    parser.add_argument("--azure-openai-key", help="Azure OpenAI API anahtarı")
    parser.add_argument("--api-token", help="ModularMind API token")
    
    args = parser.parse_args()
    
    # Gerekli paketi kontrol et
    try:
        import huggingface_hub
    except ImportError:
        logger.error("huggingface_hub paketi bulunamadı. Lütfen şunu çalıştırın: pip install huggingface_hub")
        sys.exit(1)
    
    # Ana süreç
    create_dirs()
    setup_embedding_models(args)
    setup_llm_models(args)
    setup_vector_store(args)
    setup_model_router(args)
    generate_env(args)
    
    logger.info("Model indirme ve yapılandırma tamamlandı!")
    logger.info("""
    Sonraki adımlar:
    1. Gerekli API anahtarlarını .env dosyasında yapılandırın (yoksa)
    2. ModularMind API'yi çalıştırın: python -m ModularMind.API.main
    """)

if __name__ == "__main__":
    main()