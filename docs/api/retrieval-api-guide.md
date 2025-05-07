# ModularMind MM-RAG Retrieval API Guide

Bu rehber, ModularMind MM-RAG v1.1 sisteminin gelişmiş veri erişim (retrieval) API'lerinin kullanımını açıklamaktadır.

## Giriş

ModularMind MM-RAG v1.1, esnek ve güçlü bir veri erişim altyapısına sahiptir. Bu API, aşağıdaki özellikleri sunar:

- Çoklu erişim stratejileri (Hibrit, Dense, Sparse)
- Dinamik retriever seçimi
- Cross-Encoder reranking
- Metadata bazlı filtreleme ve sıralama
- Bağlam optimizasyonu
- Kaynak atıfları
- Performans izleme

## API Endpointleri

### 1. `/api/v1/retrieval/search` - Ana Arama Endpointi

**HTTP Metodu:** POST

**Açıklama:** Bu endpoint, belgelerde veya bilgi tabanında arama yapmak için kullanılır. Farklı retrieval stratejilerini destekler ve isteğe bağlı olarak sonuçları yeniden sıralayabilir ve bağlam penceresini optimize edebilir.

**İstek Gövdesi:**

```json
{
  "query": "Türkiye'de elektrikli araçlar için vergi indirimleri nelerdir?",
  "k": 5,
  "method": "hybrid",
  "filters": {
    "language": "tr",
    "category": ["otomotiv", "vergi"]
  },
  "rerank": true,
  "optimize_context": true,
  "metadata_query": {
    "text": "elektrikli araçlar vergi indirimi",
    "filters": [
      {
        "field": "date",
        "operator": "gte",
        "value": "2023-01-01"
      }
    ],
    "boost_by": {
      "relevance": 0.8,
      "recency": 0.2
    }
  },
  "explain": false
}