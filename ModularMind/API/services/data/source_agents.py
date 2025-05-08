"""
Veri Kaynak Ajanları yönetim modülü.
"""

import asyncio
import logging
import time
import uuid
import json
import os
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
from dataclasses import dataclass, field
import threading
import schedule

from ModularMind.API.services.retrieval.models import Document, Chunk
from ModularMind.API.services.embedding import EmbeddingService

logger = logging.getLogger(__name__)

class AgentType(str, Enum):
    """Ajan türleri."""
    WEB_CRAWLER = "web_crawler"
    RSS_READER = "rss_reader"
    DATABASE = "database"
    FILE_SYSTEM = "file_system"
    API_CONNECTOR = "api_connector"
    EMAIL = "email"
    CUSTOM = "custom"

class AgentStatus(str, Enum):
    """Ajan durumları."""
    IDLE = "idle"
    RUNNING = "running"
    ERROR = "error"
    DISABLED = "disabled"

@dataclass
class AgentConfig:
    """Ajan yapılandırması."""
    agent_id: str
    agent_type: AgentType
    name: str
    description: Optional[str] = ""
    source_url: Optional[str] = None
    credentials: Dict[str, Any] = field(default_factory=dict)
    schedule: Optional[str] = None  # "interval:10m", "cron:0 9 * * *", "daily:09:00"
    filters: Dict[str, Any] = field(default_factory=dict)
    options: Dict[str, Any] = field(default_factory=dict)
    metadata_mapping: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True
    last_run: Optional[float] = None
    error_count: int = 0
    max_items: int = 100
    
    def to_dict(self) -> Dict[str, Any]:
        """Ayarları sözlüğe dönüştürür."""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "name": self.name,
            "description": self.description,
            "source_url": self.source_url,
            "credentials": self.credentials,
            "schedule": self.schedule,
            "filters": self.filters,
            "options": self.options,
            "metadata_mapping": self.metadata_mapping,
            "enabled": self.enabled,
            "last_run": self.last_run,
            "error_count": self.error_count,
            "max_items": self.max_items
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentConfig':
        """Sözlükten yapılandırma oluşturur."""
        return cls(**data)

@dataclass
class AgentResult:
    """Ajan çalışma sonucu."""
    agent_id: str
    success: bool
    documents: List[Document]
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    item_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Sonuçları sözlüğe dönüştürür."""
        return {
            "agent_id": self.agent_id,
            "success": self.success,
            "documents": [doc.to_dict() for doc in self.documents],
            "error_message": self.error_message,
            "metadata": self.metadata,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "item_count": self.item_count,
            "duration": (self.end_time - self.start_time) if self.end_time else None
        }

class SourceAgentManager:
    """
    Veri kaynak ajanlarını yöneten sınıf.
    """
    
    def __init__(
        self, 
        vector_store=None,
        embedding_service: Optional[EmbeddingService] = None,
        config_path: str = "./config/agents"
    ):
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.config_path = config_path
        
        # Ajan yapılandırmaları
        self.agents: Dict[str, AgentConfig] = {}
        
        # Çalışan ajanlar
        self.running_agents: Dict[str, threading.Thread] = {}
        
        # Son çalışma sonuçları
        self.last_results: Dict[str, AgentResult] = {}
        
        # Çalışma zamanı kuyruğu
        self.schedule_queue = []
        
        # Kilitleme mekanizması
        self.lock = threading.RLock()
        
        # Zamanlama thread'i
        self.scheduler_thread = None
        self.scheduler_running = False
        
        # Yapılandırmaları yükle
        self._load_configs()
        
        # Zamanlamayı başlat
        self._start_scheduler()
        
        logger.info(f"SourceAgentManager başlatıldı, {len(self.agents)} ajan yapılandırması yüklendi")
    
    def add_agent(self, config: AgentConfig) -> str:
        """
        Yeni bir ajan ekler.
        
        Args:
            config: Ajan yapılandırması
            
        Returns:
            str: Ajan ID
        """
        with self.lock:
            # ID yoksa oluştur
            if not config.agent_id:
                config.agent_id = str(uuid.uuid4())
            
            # Ajanı ekle
            self.agents[config.agent_id] = config
            
            # Yapılandırmayı kaydet
            self._save_config(config)
            
            # Zamanlamayı güncelle
            if config.schedule and config.enabled:
                self._schedule_agent(config)
            
            logger.info(f"Ajan eklendi: {config.name} ({config.agent_id})")
            
            return config.agent_id
    
    def update_agent(self, agent_id: str, config_updates: Dict[str, Any]) -> Optional[AgentConfig]:
        """
        Ajan yapılandırmasını günceller.
        
        Args:
            agent_id: Ajan ID
            config_updates: Güncellenecek ayarlar
            
        Returns:
            Optional[AgentConfig]: Güncellenmiş ajan yapılandırması
        """
        with self.lock:
            if agent_id not in self.agents:
                logger.warning(f"Ajan bulunamadı: {agent_id}")
                return None
            
            # Mevcut yapılandırmayı al
            config = self.agents[agent_id]
            
            # Yapılandırmayı güncelle
            for key, value in config_updates.items():
                if hasattr(config, key):
                    setattr(config, key, value)
            
            # Zamanlamayı güncelle
            self._update_schedule(config)
            
            # Yapılandırmayı kaydet
            self._save_config(config)
            
            logger.info(f"Ajan güncellendi: {config.name} ({agent_id})")
            
            return config
    
    def delete_agent(self, agent_id: str) -> bool:
        """
        Ajanı siler.
        
        Args:
            agent_id: Ajan ID
            
        Returns:
            bool: Başarı durumu
        """
        with self.lock:
            if agent_id not in self.agents:
                logger.warning(f"Ajan bulunamadı: {agent_id}")
                return False
            
            # Çalışıyorsa durdur
            if agent_id in self.running_agents:
                self.stop_agent(agent_id)
            
            # Zamanlamadan kaldır
            self._remove_schedule(agent_id)
            
            # Ajanı kaldır
            del self.agents[agent_id]
            
            # Yapılandırma dosyasını sil
            config_file = os.path.join(self.config_path, f"{agent_id}.json")
            if os.path.exists(config_file):
                os.remove(config_file)
            
            logger.info(f"Ajan silindi: {agent_id}")
            
            return True
    
    def get_agent(self, agent_id: str) -> Optional[AgentConfig]:
        """
        Ajan yapılandırmasını döndürür.
        
        Args:
            agent_id: Ajan ID
            
        Returns:
            Optional[AgentConfig]: Ajan yapılandırması
        """
        return self.agents.get(agent_id)
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """
        Tüm ajanları listeler.
        
        Returns:
            List[Dict[str, Any]]: Ajan listesi
        """
        agents_list = []
        
        for agent_id, config in self.agents.items():
            # Temel bilgileri al
            agent_info = {
                "agent_id": agent_id,
                "name": config.name,
                "agent_type": config.agent_type,
                "enabled": config.enabled,
                "schedule": config.schedule,
                "last_run": config.last_run,
                "status": self._get_agent_status(agent_id),
                "source_url": config.source_url,
                "description": config.description
            }
            
            # Son çalışma sonucunu ekle
            if agent_id in self.last_results:
                result = self.last_results[agent_id]
                agent_info["last_result"] = {
                    "success": result.success,
                    "item_count": result.item_count,
                    "end_time": result.end_time,
                    "error_message": result.error_message
                }
            
            agents_list.append(agent_info)
        
        return agents_list
    
    def run_agent(self, agent_id: str, sync: bool = False) -> Optional[str]:
        """
        Ajanı çalıştırır.
        
        Args:
            agent_id: Ajan ID
            sync: Senkron çalıştırma bayrağı
            
        Returns:
            Optional[str]: İş ID'si veya None
        """
        with self.lock:
            if agent_id not in self.agents:
                logger.warning(f"Ajan bulunamadı: {agent_id}")
                return None
            
            config = self.agents[agent_id]
            
            # Zaten çalışıyorsa kontrol et
            if agent_id in self.running_agents and self.running_agents[agent_id].is_alive():
                logger.warning(f"Ajan zaten çalışıyor: {config.name} ({agent_id})")
                return None
            
            # İş ID'si oluştur
            job_id = f"job_{uuid.uuid4().hex}"
            
            if sync:
                # Senkron çalıştır
                self._run_agent_job(agent_id, job_id)
                return job_id
            else:
                # Asenkron çalıştır
                thread = threading.Thread(
                    target=self._run_agent_job,
                    args=(agent_id, job_id),
                    daemon=True
                )
                thread.start()
                
                # Çalışan ajan listesine ekle
                self.running_agents[agent_id] = thread
                
                logger.info(f"Ajan başlatıldı: {config.name} ({agent_id}), İş ID: {job_id}")
                
                return job_id
    
    def stop_agent(self, agent_id: str) -> bool:
        """
        Çalışan ajanı durdurur.
        
        Args:
            agent_id: Ajan ID
            
        Returns:
            bool: Başarı durumu
        """
        with self.lock:
            if agent_id not in self.running_agents:
                logger.warning(f"Çalışan ajan bulunamadı: {agent_id}")
                return False
            
            # Thread'i sonlandırmak için bir mekanizma yok
            # Sadece referansı kaldırıyoruz
            del self.running_agents[agent_id]
            
            logger.info(f"Ajan durduruldu: {agent_id}")
            
            return True
    
    def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """
        Ajan durumunu döndürür.
        
        Args:
            agent_id: Ajan ID
            
        Returns:
            Dict[str, Any]: Durum bilgileri
        """
        if agent_id not in self.agents:
            return {"status": "not_found", "error": "Ajan bulunamadı"}
        
        config = self.agents[agent_id]
        
        status_info = {
            "agent_id": agent_id,
            "name": config.name,
            "status": self._get_agent_status(agent_id),
            "enabled": config.enabled,
            "last_run": config.last_run,
            "error_count": config.error_count
        }
        
        # Son çalışma sonucunu ekle
        if agent_id in self.last_results:
            result = self.last_results[agent_id]
            status_info["last_result"] = {
                "success": result.success,
                "item_count": result.item_count,
                "start_time": result.start_time,
                "end_time": result.end_time,
                "duration": (result.end_time - result.start_time) if result.end_time else None,
                "error_message": result.error_message
            }
        
        return status_info
    
    def get_agent_result(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Son çalışma sonucunu döndürür.
        
        Args:
            agent_id: Ajan ID
            
        Returns:
            Optional[Dict[str, Any]]: Çalışma sonucu
        """
        if agent_id not in self.last_results:
            return None
        
        return self.last_results[agent_id].to_dict()
    
    def shutdown(self) -> None:
        """
        Tüm ajanları durdurur ve kapatır.
        """
        logger.info("SourceAgentManager kapatılıyor...")
        
        # Zamanlayıcıyı durdur
        self.scheduler_running = False
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=2.0)
        
        # Tüm çalışan ajanları durdur
        for agent_id in list(self.running_agents.keys()):
            self.stop_agent(agent_id)
        
        logger.info("SourceAgentManager kapatıldı")
    
    def _run_agent_job(self, agent_id: str, job_id: str) -> None:
        """
        Ajan işini çalıştırır.
        
        Args:
            agent_id: Ajan ID
            job_id: İş ID
        """
        if agent_id not in self.agents:
            logger.error(f"Ajan bulunamadı: {agent_id}")
            return
        
        config = self.agents[agent_id]
        
        # Sonuç nesnesini oluştur
        result = AgentResult(
            agent_id=agent_id,
            success=False,
            documents=[],
            start_time=time.time()
        )
        
        try:
            logger.info(f"Ajan çalıştırılıyor: {config.name} ({agent_id}), İş ID: {job_id}")
            
            # Ajan tipine göre veri toplama
            if config.agent_type == AgentType.WEB_CRAWLER:
                self._run_web_crawler(config, result)
            elif config.agent_type == AgentType.RSS_READER:
                self._run_rss_reader(config, result)
            elif config.agent_type == AgentType.DATABASE:
                self._run_database_connector(config, result)
            elif config.agent_type == AgentType.FILE_SYSTEM:
                self._run_file_system(config, result)
            elif config.agent_type == AgentType.API_CONNECTOR:
                self._run_api_connector(config, result)
            elif config.agent_type == AgentType.EMAIL:
                self._run_email_reader(config, result)
            elif config.agent_type == AgentType.CUSTOM:
                self._run_custom_agent(config, result)
            else:
                raise ValueError(f"Desteklenmeyen ajan tipi: {config.agent_type}")
            
            # Belgeleri vektör deposuna ekle
            if self.vector_store and result.documents:
                self._add_documents_to_vector_store(result.documents)
            
            # Başarılı sonuç
            result.success = True
            result.item_count = len(result.documents)
            
            # Yapılandırmayı güncelle
            with self.lock:
                config.last_run = time.time()
                config.error_count = 0
                self._save_config(config)
            
            logger.info(f"Ajan başarıyla çalıştı: {config.name} ({agent_id}), {result.item_count} belge")
            
        except Exception as e:
            logger.error(f"Ajan çalıştırma hatası: {config.name} ({agent_id}): {str(e)}", exc_info=True)
            
            result.success = False
            result.error_message = str(e)
            
            # Hata sayacını artır
            with self.lock:
                config.error_count += 1
                self._save_config(config)
        
        finally:
            # Sonucu kaydet
            result.end_time = time.time()
            self.last_results[agent_id] = result
            
            # Çalışan ajanlar listesinden kaldır
            with self.lock:
                if agent_id in self.running_agents:
                    del self.running_agents[agent_id]
    
    def _run_web_crawler(self, config: AgentConfig, result: AgentResult) -> None:
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
    
    def _run_rss_reader(self, config: AgentConfig, result: AgentResult) -> None:
        """
        RSS okuyucu ajanını çalıştırır.
        
        Args:
            config: Ajan yapılandırması
            result: Sonuç nesnesi
        """
        try:
            import feedparser
            from datetime import datetime
            import time
            
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
    
    def _run_database_connector(self, config: AgentConfig, result: AgentResult) -> None:
        """
        Veritabanı bağlantı ajanını çalıştırır.
        
        Args:
            config: Ajan yapılandırması
            result: Sonuç nesnesi
        """
        # Bu fonksiyon, gerçek uygulama senaryosunda tamamlanmalıdır
        # Burada sadece temel yapı gösterilmiştir
        
        # Veritabanı tipini kontrol et
        db_type = config.options.get("db_type", "")
        
        if db_type == "postgres":
            self._run_postgres_connector(config, result)
        elif db_type == "mysql":
            self._run_mysql_connector(config, result)
        elif db_type == "sqlite":
            self._run_sqlite_connector(config, result)
        else:
            raise ValueError(f"Desteklenmeyen veritabanı tipi: {db_type}")
    
    def _run_file_system(self, config: AgentConfig, result: AgentResult) -> None:
        """
        Dosya sistemi ajanını çalıştırır.
        
        Args:
            config: Ajan yapılandırması
            result: Sonuç nesnesi
        """
        # Bu fonksiyon, gerçek uygulama senaryosunda tamamlanmalıdır
        # Burada sadece temel yapı gösterilmiştir
        
        # Klasör yolunu kontrol et
        folder_path = config.source_url
        if not folder_path or not os.path.isdir(folder_path):
            raise ValueError(f"Geçerli bir klasör yolu değil: {folder_path}")
        
        # Dosya uzantılarını al
        extensions = config.options.get("extensions", [".txt", ".md", ".pdf", ".docx"])
        
        # Son değişiklik zamanını kontrol et
        check_mtime = config.options.get("check_mtime", True)
        
        # Dokümanlar
        documents = []
        
        # Dosyaları tara
        for root, _, files in os.walk(folder_path):
            for file in files:
                # Uzantıyı kontrol et
                _, ext = os.path.splitext(file)
                if ext.lower() not in extensions:
                    continue
                
                # Tam dosya yolu
                file_path = os.path.join(root, file)
                
                # Değişiklik zamanını kontrol et
                if check_mtime and config.last_run:
                    mtime = os.path.getmtime(file_path)
                    if mtime <= config.last_run:
                        continue
                
                # Belge metni burada yüklenmeli
                # Gerçek bir uygulamada dosya tipine göre uygun parser kullanılmalı
                
                # Basit metin örneği
                if ext.lower() in [".txt", ".md"]:
                    with open(file_path, "r", encoding="utf-8") as f:
                        text = f.read()
                        
                    # Metadata
                    metadata = {
                        "source": file_path,
                        "title": os.path.basename(file),
                        "source_type": "file",
                        "file_type": ext.lstrip("."),
                        "modified_time": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(os.path.getmtime(file_path)))
                    }
                    
                    # Belge oluştur
                    doc_id = f"file_{uuid.uuid4().hex}"
                    document = Document(
                        id=doc_id,
                        text=text,
                        metadata=metadata
                    )
                    
                    # Belgeyi listeye ekle
                    documents.append(document)
        
        # Sonucu güncelle
        result.documents = documents
    
    def _run_api_connector(self, config: AgentConfig, result: AgentResult) -> None:
        """
        API bağlantı ajanını çalıştırır.
        
        Args:
            config: Ajan yapılandırması
            result: Sonuç nesnesi
        """
        # Bu fonksiyon, gerçek uygulama senaryosunda tamamlanmalıdır
        # Burada sadece temel yapı gösterilmiştir
        pass
    
    def _run_email_reader(self, config: AgentConfig, result: AgentResult) -> None:
        """
        E-posta okuyucu ajanını çalıştırır.
        
        Args:
            config: Ajan yapılandırması
            result: Sonuç nesnesi
        """
        # Bu fonksiyon, gerçek uygulama senaryosunda tamamlanmalıdır
        # Burada sadece temel yapı gösterilmiştir
        pass
    
    def _run_custom_agent(self, config: AgentConfig, result: AgentResult) -> None:
        """
        Özel ajanı çalıştırır.
        
        Args:
            config: Ajan yapılandırması
            result: Sonuç nesnesi
        """
        # Bu fonksiyon, özel ajan tiplerinin entegrasyonu için kullanılabilir
        # Burada sadece temel yapı gösterilmiştir
        
        # Özel modül bilgilerini al
        module_name = config.options.get("module")
        class_name = config.options.get("class")
        
        if not module_name or not class_name:
            raise ValueError("Özel ajan için module ve class seçenekleri gereklidir")
        
        try:
            # Dinamik modül yükleme
            import importlib
            
            module = importlib.import_module(module_name)
            agent_class = getattr(module, class_name)
            
            # Ajanı oluştur
            agent = agent_class(config)
            
            # Ajanı çalıştır
            agent_result = agent.run()
            
            # Sonuçları dönüştür
            result.documents = agent_result.get("documents", [])
            result.metadata = agent_result.get("metadata", {})
            
        except (ImportError, AttributeError) as e:
            raise ImportError(f"Özel ajan modülü yüklenemedi: {str(e)}")
    
    def _add_documents_to_vector_store(self, documents: List[Document]) -> None:
        """
        Belgeleri vektör deposuna ekler.
        
        Args:
            documents: Belge listesi
        """
        if not self.vector_store:
            logger.warning("Vektör deposu bulunamadı, belgeler eklenemiyor")
            return
        
        # Belgeleri parçalara ayır
        all_chunks = []
        
        for document in documents:
            # Belge zaten parçalanmış mı?
            if document.chunks:
                # Embedding'leri hesapla
                for chunk in document.chunks:
                    if chunk.embedding is None and self.embedding_service:
                        chunk.embedding = self.embedding_service.get_embedding(chunk.text)
                    
                    all_chunks.append(chunk)
            else:
                # Belgeyi parçala
                from ModularMind.API.services.retrieval.chunking import split_text
                
                chunks = split_text(document.text, chunk_size=500, chunk_overlap=50)
                
                # Parçaları oluştur
                for i, chunk_text in enumerate(chunks):
                    # Metadata
                    metadata = document.metadata.copy()
                    metadata["chunk_index"] = i
                    
                    # Chunk oluştur
                    chunk = Chunk(
                        id=f"{document.id}_chunk_{i}",
                        text=chunk_text,
                        document_id=document.id,
                        metadata=metadata
                    )
                    
                    # Embedding hesapla
                    if self.embedding_service:
                        chunk.embedding = self.embedding_service.get_embedding(chunk_text)
                    
                    # Listeye ekle
                    all_chunks.append(chunk)
                    document.chunks.append(chunk)
        
        # Vektör deposuna ekle
        if all_chunks:
            self.vector_store.add_batch(all_chunks)
    
    def _load_configs(self) -> None:
        """
        Ajan yapılandırmalarını yükler.
        """
        # Yapılandırma dizinini kontrol et
        if not os.path.exists(self.config_path):
            os.makedirs(self.config_path, exist_ok=True)
            return
        
        # Yapılandırma dosyalarını yükle
        for filename in os.listdir(self.config_path):
            if filename.endswith(".json"):
                try:
                    file_path = os.path.join(self.config_path, filename)
                    
                    with open(file_path, "r") as f:
                        config_data = json.load(f)
                    
                    # AgentConfig oluştur
                    config = AgentConfig.from_dict(config_data)
                    
                    # Ajanı ekle
                    self.agents[config.agent_id] = config
                    
                except Exception as e:
                    logger.error(f"Ajan yapılandırması yükleme hatası: {filename}: {str(e)}")
    
    def _save_config(self, config: AgentConfig) -> None:
        """
        Ajan yapılandırmasını kaydeder.
        
        Args:
            config: Ajan yapılandırması
        """
        # Yapılandırma dizinini kontrol et
        if not os.path.exists(self.config_path):
            os.makedirs(self.config_path, exist_ok=True)
        
        # Dosya yolu
        file_path = os.path.join(self.config_path, f"{config.agent_id}.json")
        
        # Yapılandırmayı kaydet
        try:
            with open(file_path, "w") as f:
                json.dump(config.to_dict(), f, indent=2)
        except Exception as e:
            logger.error(f"Ajan yapılandırması kaydetme hatası: {config.agent_id}: {str(e)}")
    
    def _start_scheduler(self) -> None:
        """
        Zamanlama thread'ini başlatır.
        """
        # Zamanlamayı ayarla
        for agent_id, config in self.agents.items():
            if config.enabled and config.schedule:
                self._schedule_agent(config)
        
        # Zamanlama thread'ini başlat
        self.scheduler_running = True
        self.scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            daemon=True
        )
        self.scheduler_thread.start()
    
    def _scheduler_loop(self) -> None:
        """
        Zamanlama döngüsü.
        """
        while self.scheduler_running:
            # Zamanlanmış işleri çalıştır
            schedule.run_pending()
            
            # Saniye başı kontrol et
            time.sleep(1)
    
    def _schedule_agent(self, config: AgentConfig) -> None:
        """
        Ajanı zamanlar.
        
        Args:
            config: Ajan yapılandırması
        """
        if not config.schedule:
            return
        
        # Mevcut zamanlamayı kaldır
        self._remove_schedule(config.agent_id)
        
        # Zamanlama tipini analiz et
        if config.schedule.startswith("interval:"):
            # Aralık zamanlama (örn: "interval:10m")
            interval_str = config.schedule.split(":", 1)[1].strip()
            
            # Birimi ve değeri ayır
            import re
            match = re.match(r"(\d+)([smhd])", interval_str)
            
            if match:
                value = int(match.group(1))
                unit = match.group(2)
                
                # Saniye olarak aralığı hesapla
                if unit == "s":
                    seconds = value
                elif unit == "m":
                    seconds = value * 60
                elif unit == "h":
                    seconds = value * 60 * 60
                elif unit == "d":
                    seconds = value * 60 * 60 * 24
                else:
                    logger.error(f"Geçersiz aralık birimi: {unit}")
                    return
                
                # Her X saniyede bir çalıştır
                schedule.every(seconds).seconds.do(self._scheduled_run, agent_id=config.agent_id)
                
        elif config.schedule.startswith("cron:"):
            # Cron zamanlama (örn: "cron:0 9 * * *")
            cron_str = config.schedule.split(":", 1)[1].strip()
            
            # Cron ifadesini parçala
            parts = cron_str.split()
            
            if len(parts) != 5:
                logger.error(f"Geçersiz cron ifadesi: {cron_str}")
                return
            
            minute, hour, day, month, day_of_week = parts
            
            # Schedule yapılandırması
            job = schedule.every()
            
            # Gün ayarla
            if day != "*":
                job = job.day(int(day))
            
            # Ay ayarla
            if month != "*":
                logger.warning("Aylık zamanlama desteklenmiyor, görmezden geliniyor")
            
            # Haftanın günü ayarla
            if day_of_week != "*":
                days = {
                    "0": "sunday",
                    "1": "monday",
                    "2": "tuesday",
                    "3": "wednesday",
                    "4": "thursday",
                    "5": "friday",
                    "6": "saturday"
                }
                if day_of_week in days:
                    job = getattr(job, days[day_of_week])
            
            # Saat ve dakika ayarla
            if hour != "*":
                job = job.at(f"{hour.zfill(2)}:{minute.zfill(2)}")
            else:
                # Her saatte, dakika belirt
                if minute != "*":
                    job = job.minute(int(minute))
            
            # İşi ekle
            job.do(self._scheduled_run, agent_id=config.agent_id)
            
        elif config.schedule.startswith("daily:"):
            # Günlük zamanlama (örn: "daily:09:00")
            time_str = config.schedule.split(":", 1)[1].strip()
            
            # Her gün belirtilen saatte çalıştır
            schedule.every().day.at(time_str).do(self._scheduled_run, agent_id=config.agent_id)
            
        else:
            logger.error(f"Desteklenmeyen zamanlama formatı: {config.schedule}")
    
    def _update_schedule(self, config: AgentConfig) -> None:
        """
        Ajan zamanlamasını günceller.
        
        Args:
            config: Ajan yapılandırması
        """
        # Mevcut zamanlamayı kaldır
        self._remove_schedule(config.agent_id)
        
        # Etkinse yeniden zamanla
        if config.enabled and config.schedule:
            self._schedule_agent(config)
    
    def _remove_schedule(self, agent_id: str) -> None:
        """
        Ajan zamanlamasını kaldırır.
        
        Args:
            agent_id: Ajan ID
        """
        # Mevcut zamanlamaları kontrol et
        jobs = schedule.get_jobs()
        
        for job in jobs:
            # İş verilerine eriş
            job_func = job.job_func
            
            # İşin etiketlerini kontrol et
            if hasattr(job_func, "__closure__") and job_func.__closure__:
                for cell in job_func.__closure__:
                    # Hücre değeri agent_id'yi içeriyor mu?
                    if hasattr(cell, "cell_contents") and cell.cell_contents == agent_id:
                        # İşi kaldır
                        schedule.cancel_job(job)
                        break
    
    def _scheduled_run(self, agent_id: str) -> None:
        """
        Zamanlanmış çalıştırma fonksiyonu.
        
        Args:
            agent_id: Ajan ID
        """
        # Zamanlanmış ajanı çalıştır
        self.run_agent(agent_id)
    
    def _get_agent_status(self, agent_id: str) -> str:
        """
        Ajan durumunu belirler.
        
        Args:
            agent_id: Ajan ID
            
        Returns:
            str: Durum metni
        """
        if agent_id not in self.agents:
            return "not_found"
        
        config = self.agents[agent_id]
        
        # Devre dışı mı?
        if not config.enabled:
            return "disabled"
        
        # Çalışıyor mu?
        if agent_id in self.running_agents and self.running_agents[agent_id].is_alive():
            return "running"
        
        # Hata var mı?
        if agent_id in self.last_results:
            result = self.last_results[agent_id]
            if not result.success:
                return "error"
        
        # Başka bir durumda boşta
        return "idle"
    
    def _run_postgres_connector(self, config: AgentConfig, result: AgentResult) -> None:
        """
        PostgreSQL bağlantı ajanını çalıştırır.
        
        Args:
            config: Ajan yapılandırması
            result: Sonuç nesnesi
        """
        # Bu fonksiyon, gerçek uygulama senaryosunda tamamlanmalıdır
        # Burada sadece temel yapı gösterilmiştir
        pass
    
    def _run_mysql_connector(self, config: AgentConfig, result: AgentResult) -> None:
        """
        MySQL bağlantı ajanını çalıştırır.
        
        Args:
            config: Ajan yapılandırması
            result: Sonuç nesnesi
        """
        # Bu fonksiyon, gerçek uygulama senaryosunda tamamlanmalıdır
        # Burada sadece temel yapı gösterilmiştir
        pass
    
    def _run_sqlite_connector(self, config: AgentConfig, result: AgentResult) -> None:
        """
        SQLite bağlantı ajanını çalıştırır.
        
        Args:
            config: Ajan yapılandırması
            result: Sonuç nesnesi
        """
        # Bu fonksiyon, gerçek uygulama senaryosunda tamamlanmalıdır
        # Burada sadece temel yapı gösterilmiştir
        pass