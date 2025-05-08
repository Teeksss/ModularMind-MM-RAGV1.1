"""
Embedding Servisi.
Farklı modellerle metin gömme (embedding) işlemleri sağlar.
"""

import logging
import os
import numpy as np
import time
import hashlib
import json
from typing import List, Dict, Any, Optional, Union, Tuple
from enum import Enum
from dataclasses import dataclass
import threading
import requests

logger = logging.getLogger(__name__)

class EmbeddingModel(str, Enum):
    """Gömme modeli türleri."""
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"
    HUGGINGFACE = "huggingface"
    SENTENCE_TRANSFORMERS = "sentence_transformers"
    COHERE = "cohere"
    GOOGLE = "google"
    LOCAL = "local"
    CUSTOM = "custom"

@dataclass
class EmbeddingModelConfig:
    """Gömme modeli yapılandırması."""
    model_id: str
    model_type: EmbeddingModel
    dimensions: int
    api_key_env: str
    base_url: Optional[str] = None
    batch_size: int = 32
    cache_enabled: bool = True
    timeout: int = 60
    rate_limit_rpm: Optional[int] = None
    normalize: bool = True
    options: Optional[Dict[str, Any]] = None

class EmbeddingService:
    """
    Metin gömme (embedding) ana sınıfı.
    """
    
    def __init__(self, default_model: str = None):
        """
        Args:
            default_model: Varsayılan model kimliği
        """
        # Model yapılandırmalarını yükle
        self.models = self._load_model_configs()
        
        # Varsayılan model
        self.default_model = default_model or next(iter(self.models.keys()), None)
        
        if not self.default_model:
            logger.warning("Hiçbir embedding modeli yapılandırılmamış!")
        
        # API anahtarlarını yükle
        self.api_keys = self._load_api_keys()
        
        # İstek sayaçları
        self.request_counters = {}
        
        # Sık kullanılanlar için önbellek
        self.cache = {}
        self.cache_lock = threading.Lock()
        self.max_cache_size = 10000
        
        # Yerel modeller için instance havuzu
        self.local_models = {}
        
        logger.info(f"Embedding servisi başlatıldı, {len(self.models)} model yapılandırması yüklendi")
    
    def get_embedding(
        self, 
        text: str, 
        model: Optional[str] = None,
        normalize: Optional[bool] = None
    ) -> List[float]:
        """
        Metni, gömme vektörüne dönüştürür.
        
        Args:
            text: Gömülecek metin
            model: Kullanılacak model ID (None ise varsayılan model kullanılır)
            normalize: Vektörü normalize et (None ise model varsayılanını kullan)
            
        Returns:
            List[float]: Gömme vektörü
        """
        # Model seçimi
        model_id = model or self.default_model
        
        if model_id not in self.models:
            logger.warning(f"Model bulunamadı: {model_id}, varsayılan model kullanılıyor: {self.default_model}")
            model_id = self.default_model
        
        # Model yapılandırmasını al
        model_config = self.models[model_id]
        
        # Normalize ayarı
        should_normalize = normalize if normalize is not None else model_config.normalize
        
        # Önbellekte kontrol et
        if model_config.cache_enabled:
            cache_key = self._get_cache_key(text, model_id)
            cached_embedding = self._get_from_cache(cache_key)
            
            if cached_embedding is not None:
                # Normalizasyon kontrolü
                if should_normalize and not self._is_normalized(cached_embedding):
                    return self._normalize_vector(cached_embedding)
                return cached_embedding
        
        # Metrik sayacını güncelle
        self._update_counter(model_id)
        
        # Model tipine göre embedding hesapla
        embedding = self._get_embedding_by_model_type(text, model_config)
        
        # Normalize et
        if should_normalize:
            embedding = self._normalize_vector(embedding)
        
        # Önbelleğe ekle
        if model_config.cache_enabled:
            cache_key = self._get_cache_key(text, model_id)
            self._add_to_cache(cache_key, embedding)
        
        return embedding
    
    def get_embeddings(
        self, 
        texts: List[str], 
        model: Optional[str] = None,
        normalize: Optional[bool] = None
    ) -> List[List[float]]:
        """
        Birden fazla metni gömme vektörlerine dönüştürür.
        
        Args:
            texts: Gömülecek metinler
            model: Kullanılacak model ID (None ise varsayılan model kullanılır)
            normalize: Vektörleri normalize et (None ise model varsayılanını kullan)
            
        Returns:
            List[List[float]]: Gömme vektörleri
        """
        # Metin yoksa boş liste döndür
        if not texts:
            return []
        
        # Tek metin varsa, tekli fonksiyonu kullan
        if len(texts) == 1:
            return [self.get_embedding(texts[0], model, normalize)]
        
        # Model seçimi
        model_id = model or self.default_model
        
        if model_id not in self.models:
            logger.warning(f"Model bulunamadı: {model_id}, varsayılan model kullanılıyor: {self.default_model}")
            model_id = self.default_model
        
        # Model yapılandırmasını al
        model_config = self.models[model_id]
        
        # Normalize ayarı
        should_normalize = normalize if normalize is not None else model_config.normalize
        
        # Önbellekte olanları ve olmayanları ayır
        cached_embeddings = {}
        texts_to_embed = []
        text_indices = []
        
        if model_config.cache_enabled:
            for i, text in enumerate(texts):
                cache_key = self._get_cache_key(text, model_id)
                cached_embedding = self._get_from_cache(cache_key)
                
                if cached_embedding is not None:
                    cached_embeddings[i] = cached_embedding
                else:
                    texts_to_embed.append(text)
                    text_indices.append(i)
        else:
            texts_to_embed = texts
            text_indices = list(range(len(texts)))
        
        # Eğer tüm metinler önbellekte varsa
        if not texts_to_embed:
            embeddings = [cached_embeddings[i] for i in range(len(texts))]
            
            # Normalizasyon kontrolü
            if should_normalize:
                embeddings = [
                    self._normalize_vector(embedding) if not self._is_normalized(embedding) else embedding
                    for embedding in embeddings
                ]
            
            return embeddings
        
        # Metrik sayacını güncelle
        self._update_counter(model_id, len(texts_to_embed))
        
        # Toplu embedding hesapla
        new_embeddings = self._get_embeddings_by_model_type(texts_to_embed, model_config)
        
        # Normalize et
        if should_normalize:
            new_embeddings = [self._normalize_vector(embedding) for embedding in new_embeddings]
        
        # Önbelleğe ekle
        if model_config.cache_enabled:
            for text, embedding in zip(texts_to_embed, new_embeddings):
                cache_key = self._get_cache_key(text, model_id)
                self._add_to_cache(cache_key, embedding)
        
        # Sonuç listesini oluştur
        result = [None] * len(texts)
        
        # Önbellekten gelenleri yerleştir
        for i, embedding in cached_embeddings.items():
            result[i] = embedding if not should_normalize or self._is_normalized(embedding) else self._normalize_vector(embedding)
        
        # Yeni hesaplananları yerleştir
        for new_idx, orig_idx in enumerate(text_indices):
            result[orig_idx] = new_embeddings[new_idx]
        
        return result
    
    def similarity(
        self, 
        text1: str, 
        text2: str, 
        model: Optional[str] = None
    ) -> float:
        """
        İki metin arasındaki benzerliği hesaplar.
        
        Args:
            text1: Birinci metin
            text2: İkinci metin
            model: Kullanılacak model ID
            
        Returns:
            float: Benzerlik skoru (0-1 arası)
        """
        # Embedding'leri hesapla
        embedding1 = self.get_embedding(text1, model, normalize=True)
        embedding2 = self.get_embedding(text2, model, normalize=True)
        
        # Kosinüs benzerliği hesapla
        return self._cosine_similarity(embedding1, embedding2)
    
    def bulk_similarity(
        self, 
        texts: List[str], 
        query: str, 
        model: Optional[str] = None
    ) -> List[float]:
        """
        Bir sorgu ile birden fazla metin arasındaki benzerlikleri hesaplar.
        
        Args:
            texts: Metinler
            query: Sorgu metni
            model: Kullanılacak model ID
            
        Returns:
            List[float]: Benzerlik skorları
        """
        # Sorgu embedding'ini hesapla
        query_embedding = self.get_embedding(query, model, normalize=True)
        
        # Metinlerin embedding'lerini hesapla
        text_embeddings = self.get_embeddings(texts, model, normalize=True)
        
        # Benzerlik skorlarını hesapla
        similarities = [
            self._cosine_similarity(query_embedding, text_embedding)
            for text_embedding in text_embeddings
        ]
        
        return similarities
    
    def get_available_models(self) -> List[Dict[str, Any]]:
        """
        Kullanılabilir modellerin bilgilerini döndürür.
        
        Returns:
            List[Dict[str, Any]]: Model bilgileri
        """
        models_info = []
        
        for model_id, config in self.models.items():
            # API anahtarının varlığını kontrol et
            api_key_env = config.api_key_env
            has_api_key = api_key_env in self.api_keys and bool(self.api_keys[api_key_env])
            
            models_info.append({
                "id": model_id,
                "type": config.model_type,
                "dimensions": config.dimensions,
                "has_api_key": has_api_key,
                "supports_batching": True
            })
        
        return models_info
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Metrik bilgilerini döndürür.
        
        Returns:
            Dict[str, Any]: Metrikler
        """
        return {
            "request_counters": self.request_counters,
            "cache_size": len(self.cache),
            "available_models": len(self.get_available_models())
        }
    
    def _load_model_configs(self) -> Dict[str, EmbeddingModelConfig]:
        """
        Model yapılandırmalarını yükler.
        
        Returns:
            Dict[str, EmbeddingModelConfig]: Model yapılandırmaları
        """
        configs = {}
        
        # Temel yapılandırmalar
        configs["text-embedding-ada-002"] = EmbeddingModelConfig(
            model_id="text-embedding-ada-002",
            model_type=EmbeddingModel.OPENAI,
            dimensions=1536,
            api_key_env="OPENAI_API_KEY",
            normalize=True
        )
        
        configs["text-embedding-3-small"] = EmbeddingModelConfig(
            model_id="text-embedding-3-small",
            model_type=EmbeddingModel.OPENAI,
            dimensions=1536,
            api_key_env="OPENAI_API_KEY",
            normalize=True
        )
        
        configs["text-embedding-3-large"] = EmbeddingModelConfig(
            model_id="text-embedding-3-large",
            model_type=EmbeddingModel.OPENAI,
            dimensions=3072,
            api_key_env="OPENAI_API_KEY",
            normalize=True
        )
        
        configs["all-MiniLM-L6-v2"] = EmbeddingModelConfig(
            model_id="all-MiniLM-L6-v2",
            model_type=EmbeddingModel.SENTENCE_TRANSFORMERS,
            dimensions=384,
            api_key_env="",
            normalize=True
        )
        
        # Özel yapılandırmaları yükle
        try:
            models_path = os.path.join(os.path.dirname(__file__), "embedding_models_config.json")
            if os.path.exists(models_path):
                with open(models_path, "r") as f:
                    custom_models = json.load(f)
                
                for model_id, config in custom_models.items():
                    # Enum değerlerini dönüştür
                    model_type = EmbeddingModel(config.get("model_type", "custom"))
                    
                    configs[model_id] = EmbeddingModelConfig(
                        model_id=model_id,
                        model_type=model_type,
                        dimensions=config.get("dimensions", 768),
                        api_key_env=config.get("api_key_env", ""),
                        base_url=config.get("base_url"),
                        batch_size=config.get("batch_size", 32),
                        cache_enabled=config.get("cache_enabled", True),
                        timeout=config.get("timeout", 60),
                        rate_limit_rpm=config.get("rate_limit_rpm"),
                        normalize=config.get("normalize", True),
                        options=config.get("options")
                    )
        except Exception as e:
            logger.error(f"Özel embedding model yapılandırması yükleme hatası: {str(e)}")
        
        return configs
    
    def _load_api_keys(self) -> Dict[str, str]:
        """
        API anahtarlarını çevresel değişkenlerden yükler.
        
        Returns:
            Dict[str, str]: API anahtarları
        """
        api_keys = {}
        
        # Model yapılandırmalarında belirtilen tüm çevresel değişkenleri topla
        env_vars = set(model.api_key_env for model in self.models.values() if model.api_key_env)
        
        # Anahtarları yükle
        for env_var in env_vars:
            api_keys[env_var] = os.environ.get(env_var, "")
            
            if not api_keys[env_var] and env_var:
                logger.warning(f"API anahtarı bulunamadı: {env_var}")
        
        return api_keys
    
    def _get_embedding_by_model_type(
        self, 
        text: str, 
        model_config: EmbeddingModelConfig
    ) -> List[float]:
        """
        Model tipine göre embedding hesaplar.
        
        Args:
            text: Gömülecek metin
            model_config: Model yapılandırması
            
        Returns:
            List[float]: Gömme vektörü
        """
        model_type = model_config.model_type
        
        try:
            if model_type == EmbeddingModel.OPENAI:
                return self._get_openai_embedding(text, model_config)
                
            elif model_type == EmbeddingModel.AZURE_OPENAI:
                return self._get_azure_openai_embedding(text, model_config)
                
            elif model_type == EmbeddingModel.SENTENCE_TRANSFORMERS:
                return self._get_sentence_transformers_embedding(text, model_config)
                
            elif model_type == EmbeddingModel.HUGGINGFACE:
                return self._get_huggingface_embedding(text, model_config)
                
            elif model_type == EmbeddingModel.COHERE:
                return self._get_cohere_embedding(text, model_config)
                
            elif model_type == EmbeddingModel.GOOGLE:
                return self._get_google_embedding(text, model_config)
                
            elif model_type == EmbeddingModel.LOCAL:
                return self._get_local_embedding(text, model_config)
                
            else:
                logger.error(f"Desteklenmeyen model tipi: {model_type}")
                # Varsayılan olarak sıfır vektörü döndür
                return [0.0] * model_config.dimensions
                
        except Exception as e:
            logger.error(f"Embedding hesaplama hatası ({model_config.model_id}): {str(e)}", exc_info=True)
            # Varsayılan olarak sıfır vektörü döndür
            return [0.0] * model_config.dimensions
    
    def _get_embeddings_by_model_type(
        self, 
        texts: List[str], 
        model_config: EmbeddingModelConfig
    ) -> List[List[float]]:
        """
        Model tipine göre toplu embedding hesaplar.
        
        Args:
            texts: Gömülecek metinler
            model_config: Model yapılandırması
            
        Returns:
            List[List[float]]: Gömme vektörleri
        """
        model_type = model_config.model_type
        
        try:
            if model_type == EmbeddingModel.OPENAI:
                return self._get_openai_embeddings(texts, model_config)
                
            elif model_type == EmbeddingModel.AZURE_OPENAI:
                return self._get_azure_openai_embeddings(texts, model_config)
                
            elif model_type == EmbeddingModel.SENTENCE_TRANSFORMERS:
                return self._get_sentence_transformers_embeddings(texts, model_config)
                
            elif model_type == EmbeddingModel.HUGGINGFACE:
                return self._get_huggingface_embeddings(texts, model_config)
                
            elif model_type == EmbeddingModel.COHERE:
                return self._get_cohere_embeddings(texts, model_config)
                
            elif model_type == EmbeddingModel.GOOGLE:
                return self._get_google_embeddings(texts, model_config)
                
            elif model_type == EmbeddingModel.LOCAL:
                return self._get_local_embeddings(texts, model_config)
                
            else:
                logger.error(f"Desteklenmeyen model tipi: {model_type}")
                # Varsayılan olarak sıfır vektörü döndür
                return [[0.0] * model_config.dimensions for _ in range(len(texts))]
                
        except Exception as e:
            logger.error(f"Toplu embedding hesaplama hatası ({model_config.model_id}): {str(e)}", exc_info=True)
            # Varsayılan olarak sıfır vektörü döndür
            return [[0.0] * model_config.dimensions for _ in range(len(texts))]
    
    def _get_openai_embedding(self, text: str, model_config: EmbeddingModelConfig) -> List[float]:
        """
        OpenAI modeliyle embedding hesaplar.
        
        Args:
            text: Gömülecek metin
            model_config: Model yapılandırması
            
        Returns:
            List[float]: Gömme vektörü
        """
        try:
            import openai
            
            # API anahtarını al
            api_key = self.api_keys.get(model_config.api_key_env, "")
            if not api_key:
                raise ValueError(f"OpenAI API anahtarı bulunamadı: {model_config.api_key_env}")
            
            # OpenAI istemci
            client = openai.OpenAI(api_key=api_key)
            
            # Embedding isteği
            response = client.embeddings.create(
                model=model_config.model_id,
                input=text
            )
            
            # Vektörü döndür
            return response.data[0].embedding
            
        except ImportError:
            logger.error("openai kütüphanesi bulunamadı, pip install openai komutuyla yükleyin")
            return [0.0] * model_config.dimensions
    
    def _get_openai_embeddings(self, texts: List[str], model_config: EmbeddingModelConfig) -> List[List[float]]:
        """
        OpenAI modeliyle toplu embedding hesaplar.
        
        Args:
            texts: Gömülecek metinler
            model_config: Model yapılandırması
            
        Returns:
            List[List[float]]: Gömme vektörleri
        """
        try:
            import openai
            
            # API anahtarını al
            api_key = self.api_keys.get(model_config.api_key_env, "")
            if not api_key:
                raise ValueError(f"OpenAI API anahtarı bulunamadı: {model_config.api_key_env}")
            
            # OpenAI istemci
            client = openai.OpenAI(api_key=api_key)
            
            # Batch size
            batch_size = model_config.batch_size
            
            # Sonuç listesi
            all_embeddings = []
            
            # Batch'ler halinde işle
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i+batch_size]
                
                # Embedding isteği
                response = client.embeddings.create(
                    model=model_config.model_id,
                    input=batch_texts
                )
                
                # Sırayla embeddinglwri al
                sorted_embeddings = sorted(response.data, key=lambda x: x.index)
                batch_embeddings = [item.embedding for item in sorted_embeddings]
                
                all_embeddings.extend(batch_embeddings)
            
            return all_embeddings
            
        except ImportError:
            logger.error("openai kütüphanesi bulunamadı, pip install openai komutuyla yükleyin")
            return [[0.0] * model_config.dimensions for _ in range(len(texts))]
    
    def _get_azure_openai_embedding(self, text: str, model_config: EmbeddingModelConfig) -> List[float]:
        """
        Azure OpenAI modeliyle embedding hesaplar.
        
        Args:
            text: Gömülecek metin
            model_config: Model yapılandırması
            
        Returns:
            List[float]: Gömme vektörü
        """
        try:
            import openai
            
            # API anahtarını ve endpoint'i al
            api_key = self.api_keys.get(model_config.api_key_env, "")
            if not api_key:
                raise ValueError(f"Azure OpenAI API anahtarı bulunamadı: {model_config.api_key_env}")
            
            if not model_config.base_url:
                raise ValueError("Azure OpenAI base URL bulunamadı")
            
            # Azure OpenAI istemci
            client = openai.AzureOpenAI(
                api_key=api_key,
                api_version=model_config.options.get("api_version", "2023-05-15"),
                azure_endpoint=model_config.base_url
            )
            
            # Embedding isteği
            response = client.embeddings.create(
                model=model_config.model_id,
                input=text
            )
            
            # Vektörü döndür
            return response.data[0].embedding
            
        except ImportError:
            logger.error("openai kütüphanesi bulunamadı, pip install openai komutuyla yükleyin")
            return [0.0] * model_config.dimensions
    
    def _get_azure_openai_embeddings(self, texts: List[str], model_config: EmbeddingModelConfig) -> List[List[float]]:
        """
        Azure OpenAI modeliyle toplu embedding hesaplar.
        
        Args:
            texts: Gömülecek metinler
            model_config: Model yapılandırması
            
        Returns:
            List[List[float]]: Gömme vektörleri
        """
        try:
            import openai
            
            # API anahtarını ve endpoint'i al
            api_key = self.api_keys.get(model_config.api_key_env, "")
            if not api_key:
                raise ValueError(f"Azure OpenAI API anahtarı bulunamadı: {model_config.api_key_env}")
            
            if not model_config.base_url:
                raise ValueError("Azure OpenAI base URL bulunamadı")
            
            # Azure OpenAI istemci
            client = openai.AzureOpenAI(
                api_key=api_key,
                api_version=model_config.options.get("api_version", "2023-05-15"),
                azure_endpoint=model_config.base_url
            )
            
            # Batch size
            batch_size = model_config.batch_size
            
            # Sonuç listesi
            all_embeddings = []
            
            # Batch'ler halinde işle
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i+batch_size]
                
                # Embedding isteği
                response = client.embeddings.create(
                    model=model_config.model_id,
                    input=batch_texts
                )
                
                # Sırayla embeddinglwri al
                sorted_embeddings = sorted(response.data, key=lambda x: x.index)
                batch_embeddings = [item.embedding for item in sorted_embeddings]
                
                all_embeddings.extend(batch_embeddings)
            
            return all_embeddings
            
        except ImportError:
            logger.error("openai kütüphanesi bulunamadı, pip install openai komutuyla yükleyin")
            return [[0.0] * model_config.dimensions for _ in range(len(texts))]
    
    def _get_sentence_transformers_embedding(self, text: str, model_config: EmbeddingModelConfig) -> List[float]:
        """
        Sentence Transformers modeliyle embedding hesaplar.
        
        Args:
            text: Gömülecek metin
            model_config: Model yapılandırması
            
        Returns:
            List[float]: Gömme vektörü
        """
        try:
            # Modeli önbellekten al veya yükle
            model = self._get_sentence_transformers_model(model_config.model_id)
            
            # Embedding hesapla
            embedding = model.encode(text)
            
            # NumPy dizisini Python listesine dönüştür
            return embedding.tolist()
            
        except ImportError:
            logger.error("sentence_transformers kütüphanesi bulunamadı, pip install sentence-transformers komutuyla yükleyin")
            return [0.0] * model_config.dimensions
    
    def _get_sentence_transformers_embeddings(self, texts: List[str], model_config: EmbeddingModelConfig) -> List[List[float]]:
        """
        Sentence Transformers modeliyle toplu embedding hesaplar.
        
        Args:
            texts: Gömülecek metinler
            model_config: Model yapılandırması
            
        Returns:
            List[List[float]]: Gömme vektörleri
        """
        try:
            # Modeli önbellekten al veya yükle
            model = self._get_sentence_transformers_model(model_config.model_id)
            
            # Batch boyutu
            batch_size = model_config.batch_size
            
            # Embedding hesapla
            embeddings = model.encode(texts, batch_size=batch_size)
            
            # NumPy dizisini Python listesine dönüştür
            return embeddings.tolist()
            
        except ImportError:
            logger.error("sentence_transformers kütüphanesi bulunamadı, pip install sentence-transformers komutuyla yükleyin")
            return [[0.0] * model_config.dimensions for _ in range(len(texts))]
    
    def _get_sentence_transformers_model(self, model_id: str):
        """
        Sentence Transformers modelini yükler veya önbellekten alır.
        
        Args:
            model_id: Model ID
            
        Returns:
            Model: Sentence Transformers modeli
        """
        # Modeli önbellekten al
        if model_id in self.local_models:
            return self.local_models[model_id]
        
        try:
            from sentence_transformers import SentenceTransformer
            
            # Modeli yükle
            model = SentenceTransformer(model_id)
            
            # Önbelleğe ekle
            self.local_models[model_id] = model
            
            return model
            
        except ImportError:
            raise ImportError("sentence_transformers kütüphanesi bulunamadı")
    
    def _get_huggingface_embedding(self, text: str, model_config: EmbeddingModelConfig) -> List[float]:
        """
        Hugging Face modeliyle embedding hesaplar.
        
        Args:
            text: Gömülecek metin
            model_config: Model yapılandırması
            
        Returns:
            List[float]: Gömme vektörü
        """
        # API anahtarını al
        api_key = self.api_keys.get(model_config.api_key_env, "")
        
        # API kullanarak embedding al
        headers = {
            "Authorization": f"Bearer {api_key}" if api_key else "",
            "Content-Type": "application/json"
        }
        
        # Base URL
        base_url = model_config.base_url or "https://api-inference.huggingface.co/pipeline/feature-extraction"
        
        # İstek gönder
        try:
            response = requests.post(
                base_url,
                headers=headers,
                json={"inputs": text, "options": {"use_cache": True}},
                timeout=model_config.timeout
            )
            
            # Yanıtı işle
            if response.status_code == 200:
                embeddings = response.json()
                
                # Yanıt formatını kontrol et
                if isinstance(embeddings, list) and len(embeddings) > 0:
                    # Çoğu model için liste döner
                    if isinstance(embeddings[0], list):
                        # Ortalama al
                        average_embedding = np.mean(embeddings, axis=0).tolist()
                        return average_embedding
                    else:
                        # Tek bir vektör
                        return embeddings
                    
                return embeddings
            else:
                logger.error(f"Hugging Face API hatası: {response.status_code} - {response.text}")
                return [0.0] * model_config.dimensions
                
        except Exception as e:
            logger.error(f"Hugging Face embedding hatası: {str(e)}")
            return [0.0] * model_config.dimensions
    
    def _get_huggingface_embeddings(self, texts: List[str], model_config: EmbeddingModelConfig) -> List[List[float]]:
        """
        Hugging Face modeliyle toplu embedding hesaplar.
        
        Args:
            texts: Gömülecek metinler
            model_config: Model yapılandırması
            
        Returns:
            List[List[float]]: Gömme vektörleri
        """
        # Sonuç listesi
        all_embeddings = []
        
        # Batch size
        batch_size = model_config.batch_size
        
        # Batch'ler halinde işle
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i+batch_size]
            
            # API anahtarını al
            api_key = self.api_keys.get(model_config.api_key_env, "")
            
            # API kullanarak embedding al
            headers = {
                "Authorization": f"Bearer {api_key}" if api_key else "",
                "Content-Type": "application/json"
            }
            
            # Base URL
            base_url = model_config.base_url or "https://api-inference.huggingface.co/pipeline/feature-extraction"
            
            # İstek gönder
            try:
                response = requests.post(
                    base_url,
                    headers=headers,
                    json={"inputs": batch_texts, "options": {"use_cache": True}},
                    timeout=model_config.timeout
                )
                
                # Yanıtı işle
                if response.status_code == 200:
                    embeddings = response.json()
                    
                    # Her metin için embeddingi işle
                    for embedding in embeddings:
                        # Bazı modeller her token için ayrı embedding döndürebilir
                        if isinstance(embedding, list) and isinstance(embedding[0], list):
                            # Ortalama al
                            avg_embedding = np.mean(embedding, axis=0).tolist()
                            all_embeddings.append(avg_embedding)
                        else:
                            all_embeddings.append(embedding)
                else:
                    logger.error(f"Hugging Face API hatası: {response.status_code} - {response.text}")
                    # Hata durumunda sıfır vektörleri ekle
                    for _ in range(len(batch_texts)):
                        all_embeddings.append([0.0] * model_config.dimensions)
                    
            except Exception as e:
                logger.error(f"Hugging Face batch embedding hatası: {str(e)}")
                # Hata durumunda sıfır vektörleri ekle
                for _ in range(len(batch_texts)):
                    all_embeddings.append([0.0] * model_config.dimensions)
        
        return all_embeddings
    
    def _get_cohere_embedding(self, text: str, model_config: EmbeddingModelConfig) -> List[float]:
        """
        Cohere modeliyle embedding hesaplar.
        
        Args:
            text: Gömülecek metin
            model_config: Model yapılandırması
            
        Returns:
            List[float]: Gömme vektörü
        """
        try:
            import cohere
            
            # API anahtarını al
            api_key = self.api_keys.get(model_config.api_key_env, "")
            if not api_key:
                raise ValueError(f"Cohere API anahtarı bulunamadı: {model_config.api_key_env}")
            
            # Cohere istemci
            client = cohere.Client(api_key)
            
            # Embedding isteği
            response = client.embed(
                texts=[text],
                model=model_config.model_id
            )
            
            # Vektörü döndür
            return response.embeddings[0]
            
        except ImportError:
            logger.error("cohere kütüphanesi bulunamadı, pip install cohere komutuyla yükleyin")
            return [0.0] * model_config.dimensions
    
    def _get_cohere_embeddings(self, texts: List[str], model_config: EmbeddingModelConfig) -> List[List[float]]:
        """
        Cohere modeliyle toplu embedding hesaplar.
        
        Args:
            texts: Gömülecek metinler
            model_config: Model yapılandırması
            
        Returns:
            List[List[float]]: Gömme vektörleri
        """
        try:
            import cohere
            
            # API anahtarını al
            api_key = self.api_keys.get(model_config.api_key_env, "")
            if not api_key:
                raise ValueError(f"Cohere API anahtarı bulunamadı: {model_config.api_key_env}")
            
            # Cohere istemci
            client = cohere.Client(api_key)
            
            # Batch size
            batch_size = model_config.batch_size
            
            # Sonuç listesi
            all_embeddings = []
            
            # Batch'ler halinde işle
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i+batch_size]
                
                # Embedding isteği
                response = client.embed(
                    texts=batch_texts,
                    model=model_config.model_id
                )
                
                # Embeddinglwri ekle
                all_embeddings.extend(response.embeddings)
            
            return all_embeddings
            
        except ImportError:
            logger.error("cohere kütüphanesi bulunamadı, pip install cohere komutuyla yükleyin")
            return [[0.0] * model_config.dimensions for _ in range(len(texts))]
    
    def _get_google_embedding(self, text: str, model_config: EmbeddingModelConfig) -> List[float]:
        """
        Google modeliyle embedding hesaplar.
        
        Args:
            text: Gömülecek metin
            model_config: Model yapılandırması
            
        Returns:
            List[float]: Gömme vektörü
        """
        try:
            import google.generativeai as genai
            
            # API anahtarını al
            api_key = self.api_keys.get(model_config.api_key_env, "")
            if not api_key:
                raise ValueError(f"Google API anahtarı bulunamadı: {model_config.api_key_env}")
            
            # Google API yapılandırması
            genai.configure(api_key=api_key)
            
            # Embedding modeli
            embedding_model = genai.get_embedding_model(model_config.model_id)
            
            # Embedding isteği
            response = embedding_model.embed_content(text)
            
            # Vektörü döndür
            return response.embedding
            
        except ImportError:
            logger.error("google-generativeai kütüphanesi bulunamadı, pip install google-generativeai komutuyla yükleyin")
            return [0.0] * model_config.dimensions
    
    def _get_google_embeddings(self, texts: List[str], model_config: EmbeddingModelConfig) -> List[List[float]]:
        """
        Google modeliyle toplu embedding hesaplar.
        
        Args:
            texts: Gömülecek metinler
            model_config: Model yapılandırması
            
        Returns:
            List[List[float]]: Gömme vektörleri
        """
        try:
            import google.generativeai as genai
            
            # API anahtarını al
            api_key = self.api_keys.get(model_config.api_key_env, "")
            if not api_key:
                raise ValueError(f"Google API anahtarı bulunamadı: {model_config.api_key_env}")
            
            # Google API yapılandırması
            genai.configure(api_key=api_key)
            
            # Embedding modeli
            embedding_model = genai.get_embedding_model(model_config.model_id)
            
            # Batch size
            batch_size = model_config.batch_size
            
            # Sonuç listesi
            all_embeddings = []
            
            # Batch'ler halinde işle
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i+batch_size]
                
                # Embedding isteği
                responses = embedding_model.batch_embed_content(batch_texts)
                
                # Embeddinglwri ekle
                for response in responses:
                    all_embeddings.append(response.embedding)
            
            return all_embeddings
            
        except ImportError:
            logger.error("google-generativeai kütüphanesi bulunamadı, pip install google-generativeai komutuyla yükleyin")
            return [[0.0] * model_config.dimensions for _ in range(len(texts))]
    
    def _get_local_embedding(self, text: str, model_config: EmbeddingModelConfig) -> List[float]:
        """
        Yerel bir servis kullanarak embedding hesaplar.
        
        Args:
            text: Gömülecek metin
            model_config: Model yapılandırması
            
        Returns:
            List[float]: Gömme vektörü
        """
        try:
            # Endpoint URL
            url = model_config.base_url
            if not url:
                raise ValueError("Yerel embedding servisi için URL gereklidir")
            
            # İstek gönder
            payload = {"text": text}
            if model_config.options:
                payload.update(model_config.options)
            
            response = requests.post(
                url,
                json=payload,
                timeout=model_config.timeout
            )
            
            # Yanıtı işle
            if response.status_code == 200:
                result = response.json()
                
                # Farklı yanıt formatlarını kontrol et
                if "embedding" in result:
                    return result["embedding"]
                elif "data" in result:
                    return result["data"]
                elif "vector" in result:
                    return result["vector"]
                else:
                    # Yanıtın kendisi muhtemelen vektördür
                    return result
            else:
                logger.error(f"Yerel embedding servisi hatası: {response.status_code} - {response.text}")
                return [0.0] * model_config.dimensions
                
        except Exception as e:
            logger.error(f"Yerel embedding hesaplama hatası: {str(e)}")
            return [0.0] * model_config.dimensions
    
    def _get_local_embeddings(self, texts: List[str], model_config: EmbeddingModelConfig) -> List[List[float]]:
        """
        Yerel bir servis kullanarak toplu embedding hesaplar.
        
        Args:
            texts: Gömülecek metinler
            model_config: Model yapılandırması
            
        Returns:
            List[List[float]]: Gömme vektörleri
        """
        try:
            # Endpoint URL
            url = model_config.base_url
            if not url:
                raise ValueError("Yerel embedding servisi için URL gereklidir")
            
            # Batch size
            batch_size = model_config.batch_size
            
            # Sonuç listesi
            all_embeddings = []
            
            # Batch'ler halinde işle
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i+batch_size]
                
                # İstek gönder
                payload = {"texts": batch_texts}
                if model_config.options:
                    payload.update(model_config.options)
                
                response = requests.post(
                    url,
                    json=payload,
                    timeout=model_config.timeout
                )
                
                # Yanıtı işle
                if response.status_code == 200:
                    result = response.json()
                    
                    # Farklı yanıt formatlarını kontrol et
                    if "embeddings" in result:
                        all_embeddings.extend(result["embeddings"])
                    elif "data" in result:
                        all_embeddings.extend(result["data"])
                    elif "vectors" in result:
                        all_embeddings.extend(result["vectors"])
                    else:
                        # Yanıtın kendisi muhtemelen vektör listesidir
                        all_embeddings.extend(result)
                else:
                    logger.error(f"Yerel embedding servisi hatası: {response.status_code} - {response.text}")
                    # Hata durumunda sıfır vektörleri ekle
                    for _ in range(len(batch_texts)):
                        all_embeddings.append([0.0] * model_config.dimensions)
                    
            return all_embeddings
                
        except Exception as e:
            logger.error(f"Yerel toplu embedding hesaplama hatası: {str(e)}")
            return [[0.0] * model_config.dimensions for _ in range(len(texts))]
    
    def _get_cache_key(self, text: str, model_id: str) -> str:
        """
        Önbellek için anahtar oluşturur.
        
        Args:
            text: Gömülecek metin
            model_id: Model ID
            
        Returns:
            str: Önbellek anahtarı
        """
        # Metin ve model'den hash oluştur
        return f"{model_id}_{hashlib.md5(text.encode()).hexdigest()}"
    
    def _get_from_cache(self, cache_key: str) -> Optional[List[float]]:
        """
        Önbellekten veri alır.
        
        Args:
            cache_key: Önbellek anahtarı
            
        Returns:
            Optional[List[float]]: Önbellekten alınan veri veya None
        """
        with self.cache_lock:
            return self.cache.get(cache_key)
    
    def _add_to_cache(self, cache_key: str, embedding: List[float]) -> None:
        """
        Önbelleğe veri ekler.
        
        Args:
            cache_key: Önbellek anahtarı
            embedding: Gömme vektörü
        """
        with self.cache_lock:
            # Önbellek boyutunu kontrol et
            if len(self.cache) >= self.max_cache_size:
                # Rastgele bir öğeyi sil (basit LRU yerine)
                self.cache.pop(next(iter(self.cache)))
                
            # Önbelleğe ekle
            self.cache[cache_key] = embedding
    
    def _normalize_vector(self, vector: List[float]) -> List[float]:
        """
        Vektörü normalize eder.
        
        Args:
            vector: Normalize edilecek vektör
            
        Returns:
            List[float]: Normalize edilmiş vektör
        """
        # NumPy'a dönüştür
        np_vector = np.array(vector, dtype=np.float32)
        
        # L2 norm hesapla
        norm = np.linalg.norm(np_vector)
        
        # Normalize et
        if norm > 0:
            np_vector = np_vector / norm
            
        # Listeye dönüştür
        return np_vector.tolist()
    
    def _is_normalized(self, vector: List[float]) -> bool:
        """
        Vektörün normalize edilmiş olup olmadığını kontrol eder.
        
        Args:
            vector: Kontrol edilecek vektör
            
        Returns:
            bool: Normalize edilmiş olma durumu
        """
        # NumPy'a dönüştür
        np_vector = np.array(vector, dtype=np.float32)
        
        # L2 norm hesapla
        norm = np.linalg.norm(np_vector)
        
        # 0.999-1.001 aralığında ise normalize edilmiştir
        return 0.999 <= norm <= 1.001
    
    def _update_counter(self, model_id: str, count: int = 1) -> None:
        """
        İstek sayacını günceller.
        
        Args:
            model_id: Model ID
            count: Eklenecek sayı
        """
        if model_id not in self.request_counters:
            self.request_counters[model_id] = 0
            
        self.request_counters[model_id] += count
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        İki vektör arasındaki kosinüs benzerliğini hesaplar.
        
        Args:
            vec1: Birinci vektör
            vec2: İkinci vektör
            
        Returns:
            float: Kosinüs benzerliği
        """
        # NumPy'a dönüştür
        np_vec1 = np.array(vec1)
        np_vec2 = np.array(vec2)
        
        # Vektörleri normalize et - performans için
        if not self._is_normalized(vec1):
            np_vec1 = np_vec1 / np.linalg.norm(np_vec1)
            
        if not self._is_normalized(vec2):
            np_vec2 = np_vec2 / np.linalg.norm(np_vec2)
        
        # Kosinüs benzerliği hesapla
        similarity = np.dot(np_vec1, np_vec2)
        
        # Değer aralığını sınırla (-1 ile 1 arası)
        return float(max(min(similarity, 1.0), -1.0))