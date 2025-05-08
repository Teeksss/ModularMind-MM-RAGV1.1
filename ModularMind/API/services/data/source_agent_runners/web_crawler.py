"""
Web Crawler ajan çalıştırıcısı.
"""

import logging
import uuid
import time
from typing import Dict, Any

from ModularMind.API.services.retrieval.models import Document

logger = logging.getLogger(__name__)

def run_web_crawler(config, result):
    """
    Web crawler ajanını çalıştırır.
    
    Args:
        config: Ajan yapılandırması
        result: Sonuç nesnesi
    """
    try:
        import requests
        from bs4 import BeautifulSoup
        import urllib.parse
        
        # URL kontrolü
        if not config.source_url:
            raise ValueError("Web crawler için source_url gereklidir")
        
        # Seçenekleri al
        max_depth = config.options.get("max_depth", 1)
        max_pages = config.options.get("max_pages", 10)
        follow_links = config.options.get("follow_links", True)
        timeout = config.options.get("timeout", 10)
        headers = config.options.get("headers", {"User-Agent": "ModularMind Web Crawler"})
        
        # Ziyaret edilen URL'leri takip et
        visited_urls = set()
        queue = [(config.source_url, 0)]  # (url, depth)
        
        # Dokümanlar
        documents = []
        
        # Crawler döngüsü
        while queue and len(visited_urls) < max_pages:
            # URL ve derinliği al
            current_url, depth = queue.pop(0)
            
            # Zaten ziyaret edilmiş mi?
            if current_url in visited_urls:
                continue
            
            # Derinlik kontrolü
            if depth > max_depth:
                continue
            
            # URL'yi ziyaret et
            try:
                response = requests.get(current_url, timeout=timeout, headers=headers)
                response.raise_for_status()
                
                # URL'yi ziyaret edildi olarak işaretle
                visited_urls.add(current_url)
                
                # İçeriği parse et
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Başlığı al
                title = soup.title.string if soup.title else current_url
                
                # Ana içeriği temizle
                for script in soup(["script", "style"]):
                    script.extract()
                
                # Metin içeriğini al
                text = soup.get_text()
                
                # Metni temizle
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = "\n".join(chunk for chunk in chunks if chunk)
                
                # Metadata oluştur
                metadata = {
                    "source": current_url,
                    "title": title,
                    "source_type": "web",
                    "crawl_depth": depth,
                    "crawl_time": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                
                # Özel metadata eşlemelerini uygula
                for meta_key, selector in config.metadata_mapping.items():
                    meta_elem = soup.select_one(selector)
                    if meta_elem:
                        metadata[meta_key] = meta_elem.get_text().strip()
                
                # Belge oluştur
                doc_id = f"web_{uuid.uuid4().hex}"
                document = Document(
                    id=doc_id,
                    text=text,
                    metadata=metadata
                )
                
                # Belgeyi listeye ekle
                documents.append(document)
                
                # Bağlantıları takip et
                if follow_links and depth < max_depth:
                    for link in soup.find_all("a", href=True):
                        # Tam URL oluştur
                        next_url = urllib.parse.urljoin(current_url, link["href"])
                        
                        # Aynı domain'de olduğunu kontrol et
                        parsed_base = urllib.parse.urlparse(config.source_url)
                        parsed_next = urllib.parse.urlparse(next_url)
                        
                        if parsed_next.netloc == parsed_base.netloc:
                            queue.append((next_url, depth + 1))
                
            except Exception as e:
                logger.warning(f"URL ziyaret hatası: {current_url}: {str(e)}")
                continue
        
        # Sonucu güncelle
        result.documents = documents
        result.metadata["visited_urls"] = list(visited_urls)
        
    except ImportError:
        raise ImportError("Web crawler için requests ve beautifulsoup4 kütüphaneleri gereklidir")