"""
Weaviate indeks yöneticisi
"""

import os
import json
import logging
import time
from typing import Dict, List, Any, Optional, Union, Tuple
import numpy as np

from ..base import BaseIndexManager
from ..config import ExternalVectorDBConfig, DistanceMetric
from ..utils import normalize_vector, convert_distance_to_similarity

logger = logging.getLogger(__name__)

class WeaviateIndexManager(BaseIndexManager):
    """
    Weaviate indeks yöneticisi.
    
    Bu sınıf, Weaviate vektör veritabanı ile iletişim kurarak
    vektör indeksleme ve arama işlemlerini yönetir.
    """
    
    def __init__(self, config: Union[Dict[str, Any], ExternalVectorDBConfig]):
        """
        Weaviate indeks yöneticisini başlatır
        
        Args:
            config: İndeks yapılandırması
        """
        if isinstance(config, dict):
            self.config = ExternalVectorDBConfig.from_dict(config)
        else:
            self.config = config
        
        self.client = None
        self.collection_name = self.config.collection_name or "ModularMind_Vectors"
        self.batch_size = self.config.batch_size or 100
        self._initialized = False
    
    def initialize(self) -> bool:
        """
        Weaviate istemcisini ve indeksi başlatır
        
        Returns:
            bool: Başlatma başarılı mı
        """
        try:
            import weaviate
            
            # API anahtarını ortam değişkeninden al
            api_key = None
            if self.config.api_key_env:
                api_key = os.environ.get(self.config.api_key_env)
            
            # API anahtarı doğrudan verilmişse onu kullan
            if not api_key and self.config.api_key:
                api_key = self.config.api_key
            
            # Bağlantı dizesi
            url = self.config.connection_string or "http://localhost:8080"
            
            # İstemci yapılandırması
            auth_config = weaviate.auth.AuthApiKey(api_key=api_key) if api_key else None
            
            # İstemciyi oluştur
            self.client = weaviate.Client(
                url=url,
                auth_client_secret=auth_config,
                additional_headers=self.config.additional_params.get("headers")
            )
            
            # İstemciyi kontrol et
            if not self.client.is_ready():
                logger.error("Weaviate sunucusu hazır değil")
                return False
            
            # Koleksiyonu kontrol et ve gerekirse oluştur
            self._ensure_collection_exists()
            
            self._initialized = True
            logger.info(f"Weaviate indeksi başlatıldı: {self.collection_name}")
            return True
        except ImportError:
            logger.error("weaviate-client kütüphanesi bulunamadı. Kurulum: pip install weaviate-client")
            return False
        except Exception as e:
            logger.error(f"Weaviate indeksi başlatma hatası: {str(e)}")
            return False
    
    def _ensure_collection_exists(self):
        """Koleksiyonun varlığını kontrol eder ve gerekirse oluşturur"""
        try:
            import weaviate
            
            # Koleksiyon var mı kontrol et
            if not self.client.collections.exists(self.collection_name):
                # Koleksiyon özelliklerini tanımla
                properties = [
                    {
                        "name": "text",
                        "dataType": ["text"]
                    },
                    {
                        "name": "document_id",
                        "dataType": ["text"],
                        "indexSearchable": True
                    },
                    {
                        "name": "metadata",
                        "dataType": ["object"]
                    }
                ]
                
                # Koleksiyonu oluştur
                self.client.collections.create(
                    name=self.collection_name,
                    properties=properties,
                    vectorizer_config=weaviate.config.Configure.Vectorizer.none(),
                    vector_index_config=weaviate.config.Configure.VectorIndex.hnsw(
                        distance_metric=self._get_weaviate_distance_metric()
                    )
                )
                
                logger.info(f"Weaviate koleksiyonu oluşturuldu: {self.collection_name}")
        except Exception as e:
            logger.error(f"Koleksiyon oluşturma hatası: {str(e)}")
            raise
    
    def _get_weaviate_distance_metric(self) -> str:
        """
        DistanceMetric enum'unu Weaviate metriğine dönüştürür
        
        Returns:
            str: Weaviate metrik adı
        """
        if self.config.metric == DistanceMetric.COSINE:
            return "cosine"
        elif self.config.metric == DistanceMetric.DOT:
            return "dot"
        elif self.config.metric == DistanceMetric.EUCLIDEAN:
            return "l2-squared"
        else:
            logger.warning(f"Desteklenmeyen metrik: {self.config.metric}, cosine kullanılıyor")
            return "cosine"
    
    def add_item(self, vector: List[float], doc_id: str, metadata: Optional[Dict[str, Any]] = None, text: Optional[str] = None) -> bool:
        """
        Vektörü indekse ekler
        
        Args:
            vector: Eklenecek vektör
            doc_id: Belge kimliği
            metadata: Meta veriler
            text: Metin içeriği
            
        Returns:
            bool: Ekleme başarılı mı
        """
        if not self._initialized:
            if not self.initialize():
                return False
        
        try:
            # Vektörü normalize et (cosine kullanıyorsak)
            if self.config.metric == DistanceMetric.COSINE:
                vector = normalize_vector(vector)
            
            # Veri nesnesi oluştur
            properties = {
                "document_id": doc_id.split("_")[0] if "_" in doc_id else doc_id,
                "metadata": metadata or {}
            }
            
            if text:
                properties["text"] = text
            
            # UUID oluştur
            import uuid
            uuid_str = str(uuid.uuid5(uuid.NAMESPACE_DNS, doc_id))
            
            # Vektörü ekle
            self.client.collections.get(self.collection_name).data.insert(
                properties=properties,
                uuid=uuid_str,
                vector=vector
            )
            
            return True
        except Exception as e:
            logger.error(f"Weaviate vektör ekleme hatası: {str(e)}")
            return False
    
    def add_items_batch(self, vectors: List[List[float]], doc_ids: List[str], metadatas: Optional[List[Dict[str, Any]]] = None, texts: Optional[List[str]] = None) -> bool:
        """
        Vektörleri toplu olarak indekse ekler
        
        Args:
            vectors: Eklenecek vektörler
            doc_ids: Belge kimlikleri
            metadatas: Meta veriler listesi
            texts: Metin içerikleri listesi
            
        Returns:
            bool: Ekleme başarılı mı
        """
        if not self._initialized:
            if not self.initialize():
                return False
        
        if len(vectors) != len(doc_ids):
            logger.error(f"Vektör sayısı ({len(vectors)}) ve belge kimliği sayısı ({len(doc_ids)}) eşleşmiyor")
            return False
        
        if metadatas and len(metadatas) != len(vectors):
            logger.error("Meta veri sayısı vektör sayısı ile eşleşmiyor")
            return False
        
        if texts and len(texts) != len(vectors):
            logger.error("Metin sayısı vektör sayısı ile eşleşmiyor")
            return False
        
        try:
            import uuid
            
            # Toplu işlem yöneticisi
            with self.client.batch as batch:
                batch.batch_size = self.batch_size
                
                # Her öğe için işlem yap
                for i, (vector, doc_id) in enumerate(zip(vectors, doc_ids)):
                    # Vektörü normalize et (cosine kullanıyorsak)
                    if self.config.metric == DistanceMetric.COSINE:
                        vector = normalize_vector(vector)
                    
                    # Veri nesnesi oluştur
                    properties = {
                        "document_id": doc_id.split("_")[0] if "_" in doc_id else doc_id,
                        "metadata": metadatas[i] if metadatas else {}
                    }
                    
                    if texts:
                        properties["text"] = texts[i]
                    
                    # UUID oluştur
                    uuid_str = str(uuid.uuid5(uuid.NAMESPACE_DNS, doc_id))
                    
                    # Toplu ekleme
                    batch.add_data_object(
                        data_object=properties,
                        class_name=self.collection_name,
                        uuid=uuid_str,
                        vector=vector
                    )
            
            return True
        except Exception as e:
            logger.error(f"Weaviate toplu vektör ekleme hatası: {str(e)}")
            return False
    
    def search(self, query_vector: List[float], top_k: int = 10, min_score: Optional[float] = None) -> List[Tuple[str, float]]:
        """
        Vektöre en benzer öğeleri arar
        
        Args:
            query_vector: Sorgu vektörü
            top_k: Döndürülecek sonuç sayısı
            min_score: Minimum benzerlik skoru
            
        Returns:
            List[Tuple[str, float]]: (doc_id, score) çiftleri listesi
        """
        if not self._initialized:
            if not self.initialize():
                return []
        
        try:
            # Vektörü normalize et (cosine kullanıyorsak)
            if self.config.metric == DistanceMetric.COSINE:
                query_vector = normalize_vector(query_vector)
            
            # Sorgu oluştur
            query_results = (
                self.client.collections
                .get(self.collection_name)
                .query
                .near_vector(
                    near_vector=query_vector,
                    limit=top_k
                )
                .with_additional(["distance", "id"])
                .with_fields(["document_id"])
                .do()
            )
            
            # Sonuçları işle
            results = []
            
            if 'data' in query_results and 'Get' in query_results['data'] and self.collection_name in query_results['data']['Get']:
                for item in query_results['data']['Get'][self.collection_name]:
                    doc_id = item.get('document_id')
                    
                    if 'id' in item and not doc_id:
                        doc_id = item['id']
                    
                    if not doc_id:
                        continue
                    
                    # Uzaklığı benzerlik skoruna dönüştür
                    distance = item.get('_additional', {}).get('distance', 0)
                    
                    # Mesafeyi skora dönüştür
                    if self.config.metric == DistanceMetric.COSINE:
                        # Cosine mesafesi 0-2 arasındadır, 0 en benzer
                        score = 1 - (distance / 2)
                    elif self.config.metric == DistanceMetric.DOT:
                        # Dot product mesafesi negatiftir, yüksek değer daha benzerdir
                        score = -distance
                    elif self.config.metric == DistanceMetric.EUCLIDEAN:
                        # Euclidean mesafesi 0'dan büyüktür, 0 en benzer
                        # Normalize etmek için bir yaklaşım:
                        score = 1 / (1 + distance)
                    else:
                        score = 1 - min(1, distance)
                    
                    # Minimum skor kontrolü
                    if min_score is not None and score < min_score:
                        continue
                    
                    results.append((doc_id, score))
            
            return results
        except Exception as e:
            logger.error(f"Weaviate arama hatası: {str(e)}")
            return []
    
    def delete_item(self, doc_id: str) -> bool:
        """
        Belge kimliği ile vektörü siler
        
        Args:
            doc_id: Silinecek belge kimliği
            
        Returns:
            bool: Silme başarılı mı
        """
        if not self._initialized:
            if not self.initialize():
                return False
        
        try:
            # UUID oluştur
            import uuid
            uuid_str = str(uuid.uuid5(uuid.NAMESPACE_DNS, doc_id))
            
            # Vektörü sil
            self.client.collections.get(self.collection_name).data.delete_by_id(uuid_str)
            
            return True
        except Exception as e:
            logger.error(f"Weaviate vektör silme hatası: {str(e)}")
            return False
    
    def save(self, path: str) -> bool:
        """
        İndeksi diske kaydeder (Weaviate için kullanılmaz)
        
        Args:
            path: Kayıt yolu
            
        Returns:
            bool: Kaydetme başarılı mı
        """
        # Weaviate indeksini kaydetmeye gerek yok, veriler zaten sunucuda saklanıyor
        logger.info("Weaviate indeksi sunucuda saklanıyor, kaydetme işlemi atlanıyor")
        return True
    
    def load(self, path: str) -> bool:
        """
        İndeksi diskten yükler (Weaviate için kullanılmaz)
        
        Args:
            path: Yükleme yolu
            
        Returns:
            bool: Yükleme başarılı mı
        """
        # Weaviate indeksini yüklemeye gerek yok, veriler zaten sunucuda saklanıyor
        logger.info("Weaviate indeksi sunucuda saklanıyor, yükleme işlemi atlanıyor")
        
        # Sadece bağlantıyı başlat
        return self.initialize()
    
    def optimize(self) -> bool:
        """
        İndeksi optimize eder (Opsiyonel)
        
        Returns:
            bool: Optimizasyon başarılı mı
        """
        # Weaviate optimize etme API'si yok, başarılı sayalım
        logger.info("Weaviate indeksi optimize edilmiş sayılıyor")
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """
        İndeks istatistiklerini alır
        
        Returns:
            Dict[str, Any]: İstatistikler
        """
        if not self._initialized:
            if not self.initialize():
                return {}
        
        try:
            # Koleksiyon istatistikleri
            schema = self.client.schema.get(self.collection_name)
            
            # Sınıf sayısı
            count_result = self.client.query.aggregate(self.collection_name).with_meta_count().do()
            object_count = count_result.get('data', {}).get('Aggregate', {}).get(self.collection_name, [{}])[0].get('meta', {}).get('count', 0)
            
            return {
                "object_count": object_count,
                "collection_name": self.collection_name,
                "vector_dimensions": self.config.dimensions
            }
        except Exception as e:
            logger.error(f"Weaviate istatistik alma hatası: {str(e)}")
            return {}