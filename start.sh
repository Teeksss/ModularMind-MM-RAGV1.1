#!/bin/bash

# Renk tanımları
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}         ModularMind RAG Platform              ${NC}"
echo -e "${BLUE}================================================${NC}"

# Python sürümünü kontrol et
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "${BLUE}Python Sürümü:${NC} $python_version"

# Gerekli dizinleri oluştur
mkdir -p data
mkdir -p logs

# Sanal ortamı kontrol et
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Sanal ortam bulunamadı. Oluşturuluyor...${NC}"
    python3 -m venv venv
    source venv/bin/activate
    echo -e "${GREEN}Sanal ortam oluşturuldu ve aktifleştirildi.${NC}"
else
    source venv/bin/activate
    echo -e "${GREEN}Sanal ortam aktifleştirildi.${NC}"
fi

# Bağımlılıkları kur
echo -e "${YELLOW}Bağımlılıklar yükleniyor...${NC}"
pip install -r requirements.txt
echo -e "${GREEN}Bağımlılıklar yüklendi.${NC}"

# .env dosyasını kontrol et
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}.env dosyası bulunamadı. Örnek dosya oluşturuluyor...${NC}"
    cat > .env << EOL
# API Anahtarları
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key

# Güvenlik
API_TOKEN=your_secure_api_token

# Diğer Ayarlar
LOG_LEVEL=INFO
EOL
    echo -e "${RED}Lütfen .env dosyasını düzenleyip API anahtarlarınızı girin.${NC}"
    exit 1
fi

# .env dosyasını yükle
export $(grep -v '^#' .env | xargs)

# Backend'i başlat
echo -e "${YELLOW}ModularMind API başlatılıyor...${NC}"
python -m ModularMind.API.main &
API_PID=$!

# Frontend'i başlat
cd ModularMind/UI
echo -e "${YELLOW}Frontend bağımlılıkları yükleniyor...${NC}"
npm install

echo -e "${YELLOW}Frontend geliştirme sunucusu başlatılıyor...${NC}"
npm run dev &
UI_PID=$!
cd ../..

echo -e "${GREEN}ModularMind başlatıldı!${NC}"
echo -e "${BLUE}API:${NC} http://localhost:8000"
echo -e "${BLUE}UI:${NC} http://localhost:3000"
echo -e "${YELLOW}Durdurmak için CTRL+C tuşlarına basın${NC}"

# Temiz kapanış için sinyal yakalama
trap "kill $API_PID $UI_PID; exit" INT TERM EXIT

# İşlemlerin tamamlanmasını bekle
wait