"""
RSS Okuyucu ajan çalıştırıcısı.
"""

import logging
import uuid
import time
from typing import Dict, Any

from ModularMind.API.services.retrieval.models import Document

logger = logging.getLogger(__name__)

def run_rss_reader(config, result):
    """
    RSS okuyucu ajanını çalıştırır.
    
    Args:
        config: Ajan yapılandırması
        result: Sonuç nesnesi
    """
    try:
        import feedparser
        from datetime import datetime
        
        # URL kontrolü
        if not config.source_url:
            raise ValueError("RSS okuyucu için source_url gereklidir")
        
        # Son çalışma zamanını al
        last_run = config.last_run or 0
        
        # Seçenekleri al
        max_items = config.options.get("max_items", config.max_items)
        include_content = config.options.get("include_content", True)
        timeout = config.options.get("timeout", 30)
        
        # RSS beslemesini oku
        feed = feedparser.parse(config.source_url, timeout=timeout)
        
        # Dokümanlar
        documents = []
        
        # Girdileri işle
        for entry in feed.entries[:max_items]:
            # Yayın tarihini kontrol et
            published = entry.get("published_parsed") or entry.get("updated_parsed")
            if published:
                publish_time = time.mktime(published)
                
                # Son çalışmadan sonra mı?
                if config.last_run and publish_time <= last_run:
                    continue
            
            # Başlık
            title = entry.get("title", "Untitled")
            
            # İçerik
            content = ""
            if include_content:
                if "content" in entry:
                    content = entry.content[0].value
                elif "summary" in entry:
                    content = entry.summary
                elif "description" in entry:
                    content = entry.description
            
            # Bağlantı
            link = entry.get("link", "")
            
            # Tarih
            publish_date = ""
            if published:
                publish_date = time.strftime("%Y-%m-%d %H:%M:%S", published)
            
            # Yazar
            author = entry.get("author", "")
            
            # Metin oluştur
            text = f"{title}\n\n{content}"
            
            # Metadata
            metadata = {
                "source": link,
                "title": title,
                "source_type": "rss",
                "publish_date": publish_date,
                "author": author,
                "feed_title": feed.feed.get("title", ""),
                "feed_url": config.source_url
            }
            
            # Belge oluştur
            doc_id = f"rss_{uuid.uuid4().hex}"
            document = Document(
                id=doc_id,
                text=text,
                metadata=metadata
            )
            
            # Belgeyi listeye ekle
            documents.append(document)
        
        # Sonucu güncelle
        result.documents = documents
        result.metadata["feed_title"] = feed.feed.get("title", "")
        
    except ImportError:
        raise ImportError("RSS okuyucu için feedparser kütüphanesi gereklidir")