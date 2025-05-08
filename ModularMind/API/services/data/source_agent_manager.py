"""
Veri Kaynak Ajanları yönetim modülü.
"""

import logging
import time
import os
import json
import uuid
import threading
import schedule
from typing import Dict, List, Any, Optional, Set

from ModularMind.API.services.data.source_agent_models import AgentType, AgentStatus, AgentConfig, AgentResult
from ModularMind.API.services.retrieval.models import Document, Chunk
from ModularMind.API.services.embedding import EmbeddingService

# Ajan modüllerini içe aktar
from ModularMind.API.services.data.source_agent_runners.web_crawler import run_web_crawler
from ModularMind.API.services.data.source_agent_runners.rss_reader import run_rss_reader
from ModularMind.API.services.data.source_agent_runners.database_agent import run_database_connector
from ModularMind.API.services.data.source_agent_runners.file_system_agent import run_file_system
from ModularMind.API.services.data.source_agent_runners.api_connector_agent import run_api_connector
from ModularMind.API.services.data.source_agent_runners.email_agent import run_email_reader
from ModularMind.API.services.data.source_agent_runners.custom_agent import run_custom_agent

logger = logging.getLogger(__name__)

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
                run_web_crawler(config, result)
            elif config.agent_type == AgentType.RSS_READER:
                run_rss_reader(config, result)
            elif config.agent_type == AgentType.DATABASE:
                run_database_connector(config, result)
            elif config.agent_type == AgentType.FILE_SYSTEM:
                run_file_system(config, result)
            elif config.agent_type == AgentType.API_CONNECTOR:
                run_api_connector(config, result)
            elif config.agent_type == AgentType.EMAIL:
                run_email_reader(config, result)
            elif config.agent_type == AgentType.CUSTOM:
                run_custom_agent(config, result)
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
        from ModularMind.API.services.data.source_agent_scheduler import schedule_agent
        schedule_agent(self, config)
    
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
        from ModularMind.API.services.data.source_agent_scheduler import remove_agent_schedule
        remove_agent_schedule(agent_id)
    
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