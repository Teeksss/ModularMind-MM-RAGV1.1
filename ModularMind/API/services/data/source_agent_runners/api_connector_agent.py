"""
API bağlantı ajan çalıştırıcısı.
"""

import logging
import uuid
import time
import json
from typing import Dict, Any

from ModularMind.API.services.retrieval.models import Document

logger = logging.getLogger(__name__)

def run_api_connector(config, result):
    """
    API bağlantı ajanını çalıştırır.
    
    Args:
        config: Ajan yapılandırması
        result: Sonuç nesnesi
    """
    try:
        import requests
        
        # API URL kontrolü
        api_url = config.source_url
        if not api_url:
            raise ValueError("API URL gereklidir")
        
        # Seçenekleri al
        method = config.options.get("method", "GET")
        headers = config.options.get("headers", {})
        params = config.options.get("params", {})
        body = config.options.get("body", None)
        timeout = config.options.get("timeout", 30)
        max_items = config.options.get("max_items", config.max_items)
        
        # Kimlik doğrulama
        auth_type = config.options.get("auth_type", "")
        
        # Kimlik doğrulama türüne göre headers'ı güncelle
        if auth_type == "bearer":
            token = config.credentials.get("token", "")
            headers["Authorization"] = f"Bearer {token}"
        elif auth_type == "basic":
            import base64
            username = config.credentials.get("username", "")
            password = config.credentials.get("password", "")
            auth_str = f"{username}:{password}"
            auth_bytes = auth_str.encode("ascii")
            auth_b64 = base64.b64encode(auth_bytes).decode("ascii")
            headers["Authorization"] = f"Basic {auth_b64}"
        elif auth_type == "api_key":
            key_name = config.options.get("api_key_name", "api_key")
            key_value = config.credentials.get("api_key", "")
            key_location = config.options.get("api_key_location", "query")
            
            if key_location == "query":
                params[key_name] = key_value
            elif key_location == "header":
                headers[key_name] = key_value
        
        # API isteğini yap
        response = None
        
        if method == "GET":
            response = requests.get(api_url, params=params, headers=headers, timeout=timeout)
        elif method == "POST":
            response = requests.post(api_url, params=params, json=body, headers=headers, timeout=timeout)
        else:
            raise ValueError(f"Desteklenmeyen HTTP metodu: {method}")
        
        # Yanıt durumunu kontrol et
        response.raise_for_status()
        
        # JSON yanıtı çözümle
        data = response.json()
        
        # Veri listesini al
        items = data
        
        # Öğeleri bulunduğu JSON yolu
        data_path = config.options.get("data_path", "")
        if data_path:
            # JSON patikasını izle
            for part in data_path.split('.'):
                if isinstance(items, dict) and part in items:
                    items = items[part]
                else:
                    items = []
                    break
        
        # Liste değilse, listeye dönüştür
        if not isinstance(items, list):
            items = [items]
        
        # Limit uygula
        items = items[:max_items]
        
        # Belgeleri oluştur
        documents = []
        
        for item in items:
            # Metin ve başlık alanlarını bul
            text_field = config.options.get("text_field", "")
            title_field = config.options.get("title_field", "")
            
            # Metin içeriğini al
            text = ""
            if text_field:
                if text_field in item:
                    text = str(item[text_field])
            else:
                # Tüm öğeyi metin olarak formatla
                text = json.dumps(item, indent=2)
            
            # Başlığı al
            title = ""
            if title_field and title_field in item:
                title = str(item[title_field])
            
            # Metadata
            metadata = {
                "source": api_url,
                "source_type": "api",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "api_method": method
            }
            
            # Özel metadata eşlemelerini uygula
            for meta_key, field_name in config.metadata_mapping.items():
                if field_name in item:
                    metadata[meta_key] = str(item[field_name])
            
            # Başlık ekle
            if title:
                metadata["title"] = title
            
            # Belge oluştur
            doc_id = f"api_{uuid.uuid4().hex}"
            document = Document(
                id=doc_id,
                text=text,
                metadata=metadata
            )
            
            # Belgeyi listeye ekle
            documents.append(document)
        
        # Sonucu güncelle
        result.documents = documents
        result.metadata["item_count"] = len(documents)
        
    except ImportError:
        raise ImportError("API bağlantısı için requests kütüphanesi gereklidir")