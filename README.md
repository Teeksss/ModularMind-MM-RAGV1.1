# ModularMind RAG Platform

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

ModularMind, gelişmiş retrieval-augmented generation (RAG) uygulamaları oluşturmak için modüler, ölçeklenebilir ve genişletilebilir bir platformdur.

## Özellikler

- **Modüler Mimari**: Her bileşen bağımsız olarak çalışabilir ve özelleştirilebilir
- **Çoklu Vektör Desteği**: Farklı vector store'lar için destek (HNSW, FAISS, Qdrant, Pinecone, Weaviate vb.)
- **Gelişmiş Chunking**: Semantik, özyinelemeli ve boyut tabanlı chunking
- **Çoklu Embedding**: Birden fazla embedding modelinin bir arada kullanılması
- **Hibrit Arama**: Vektör ve anahtar kelime aramalarını birleştiren hibrit yaklaşım
- **Çoklu Modalite**: Metin, görüntü ve ses verilerini işleme yetenekleri
- **Model Fine-Tuning**: Özel verilere göre modelleri ince ayarlama
- **Kapsamlı İzleme**: Grafana panoları ile tüm sistemi izleme

## Başlarken

### Kurulum

```bash
# Depoyu klonlayın
git clone https://github.com/your-organization/modularmind.git
cd modularmind

# Bağımlılıkları yükleyin
pip install -r requirements.txt

# Modelleri ve yapılandırmaları hazırlayın
python scripts/download_models.py --openai-key YOUR_OPENAI_KEY