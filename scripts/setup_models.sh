#!/bin/bash
# ModularMind RAG Platform - Model Kurulum Scripti
# Bu script gerekli modelleri ve yapılandırmaları kurar

set -e

# Renkli çıktı
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Dizin yapısı
MODEL_DIR="./models"
EMBEDDING_MODEL_DIR="$MODEL_DIR/embeddings"
LLM_MODEL_DIR="$MODEL_DIR/llm"
CONFIG_DIR="./config"
DATA_DIR="./data"
VECTOR_STORE_DIR="$DATA_DIR/vector_store"

# Banner
echo -e "${GREEN}====================================${NC}"
echo -e "${GREEN}  ModularMind Model Kurulum Aracı   ${NC}"
echo -e "${GREEN}====================================${NC}"
echo -e "Bu script ModularMind RAG platformu için gerekli modelleri ve yapılandırmaları kurar.\n"

# Python kontrolü
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Hata: Python3 bulunamadı. Lütfen Python 3.8 veya üstünü yükleyin.${NC}"
    exit 1
fi

# Pip kontrolü
if ! command -v pip3 &> /dev/null; then
    echo -e "${RED}Hata: pip3 bulunamadı. Lütfen Python pip kurun.${NC}"
    exit 1
fi

# Gerekli dizinleri oluştur
mkdir -p "$EMBEDDING_MODEL_DIR" "$LLM_MODEL_DIR" "$CONFIG_DIR" "$VECTOR_STORE_DIR"
echo -e "${GREEN}Dizinler oluşturuldu.${NC}"

# Bağımlılıkları kur
echo -e "${YELLOW}Gerekli bağımlılıklar kuruluyor...${NC}"
pip3 install -q huggingface_hub sentence-transformers tqdm pyyaml python-dotenv numpy fastapi uvicorn

# Yapılandırmaları oluştur
setup_config() {
    echo -e "${YELLOW}Yapılandırma dosyaları oluşturuluyor...${NC}"
    
    # Geçici çalışma betikleri
    CONFIG_SCRIPT=$(cat <<EOF
import json
import os
from pathlib import Path

# Embedding model yapılandırması
embedding_config = {
    "models": [
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
        }
    ],
    "default_model": "text-embedding-3-small"
}

# LLM model yapılandırması
llm_config = {
    "models": [
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
}

# Vector store yapılandırması
vector_store_config = {
    "index_type": "HNSW",
    "dimensions": {
        "text-embedding-3-small": 1536,
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
        "all-MiniLM-L6-v2"
    ]
}

# Model router yapılandırması
model_router_config = {
    "default_model_id": "text-embedding-3-small",
    "language_models": {
        "en": "text-embedding-3-small"
    },
    "domain_models": {
        "finance": "text-embedding-3-small",
        "tech": "all-MiniLM-L6-v2"
    },
    "fallback_model_id": "text-embedding-3-small",
    "enable_auto_routing": True,
    "enable_ensemble": True,
    "ensemble_method": "weighted_average",
    "result_aggregation": "weighted_average"
}

# Yapılandırmaları kaydet
config_dir = Path("./config")
config_dir.mkdir(exist_ok=True)

with open(config_dir / "embedding_models.json", "w") as f:
    json.dump(embedding_config, f, indent=2)

with open(config_dir / "llm_models.json", "w") as f:
    json.dump(llm_config, f, indent=2)

with open(config_dir / "vector_store.json", "w") as f:
    json.dump(vector_store_config, f, indent=2)

with open(config_dir / "model_router.json", "w") as f:
    json.dump(model_router_config, f, indent=2)

print("Yapılandırmalar başarıyla oluşturuldu!")
EOF
)

    # Python ile yapılandırmaları oluştur
    python3 -c "$CONFIG_SCRIPT"
}

# Yerel modelleri indir
download_models() {
    echo -e "${YELLOW}Yerel modeller indiriliyor...${NC}"
    
    # Model indirme betiği
    DOWNLOAD_SCRIPT=$(cat <<EOF
from huggingface_hub import snapshot_download
from pathlib import Path
import os

# MiniLM'yi indir
model_id = "sentence-transformers/all-MiniLM-L6-v2"
target_dir = Path("./models/embeddings/all-MiniLM-L6-v2")

if not target_dir.exists():
    print(f"İndiriliyor: {model_id}")
    snapshot_download(
        repo_id=model_id,
        local_dir=str(target_dir),
        local_dir_use_symlinks=False
    )
    print(f"Model indirildi: {target_dir}")
else:
    print(f"Model zaten mevcut: {target_dir}")

print("Model indirme tamamlandı!")
EOF
)
    
    # Python ile modelleri indir
    python3 -c "$DOWNLOAD_SCRIPT"
}

# Ortam değişkenlerini ayarla
setup_env() {
    echo -e "${YELLOW}Ortam değişkenleri ayarlanıyor...${NC}"
    
    if [ ! -f ".env" ]; then
        echo -e "# ModularMind Ortam Değişkenleri\nLOG_LEVEL=INFO\nAPI_TOKEN=modularmind_default_token\nHOST=0.0.0.0\nPORT=8000\n\n# API Anahtarları\n# OPENAI_API_KEY=\n# ANTHROPIC_API_KEY=\n# COHERE_API_KEY=\n# AZURE_OPENAI_API_KEY=" > .env
        echo -e "${GREEN}.env dosyası oluşturuldu. Lütfen API anahtarlarınızı ekleyin.${NC}"
    else
        echo -e "${YELLOW}.env dosyası zaten var. Değiştirilmedi.${NC}"
    fi
}

# Ana işlevler
main() {
    setup_config
    download_models
    setup_env
    
    echo -e "\n${GREEN}Kurulum tamamlandı!${NC}"
    echo -e "${YELLOW}Sonraki adımlar:${NC}"
    echo -e "1. .env dosyasında API anahtarlarınızı yapılandırın"
    echo -e "2. ModularMind API'yi çalıştırın: python -m ModularMind.API.main"
    echo -e "3. Uygulamayı şu adrese giderek kullanın: http://localhost:8000"
}

# İşlemi başlat
main