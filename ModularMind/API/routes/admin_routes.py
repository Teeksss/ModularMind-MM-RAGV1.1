"""
Admin API rotaları.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import os
import uuid
import json
import shutil
import datetime

from ModularMind.API.main import get_vector_store, get_agent_manager, get_connector_registry, verify_token

router = APIRouter()

class SystemStatsResponse(BaseModel):
    """Sistem istatistikleri yanıt modeli."""
    vector_store: Dict[str, Any]
    agents: Dict[str, Any]
    connectors: Dict[str, Any]

class BackupRequest(BaseModel):
    """Yedekleme isteği modeli."""
    backup_path: Optional[str] = None
    include_vector_store: bool = True
    include_agents: bool = True
    include_connectors: bool = True

class BackupResponse(BaseModel):
    """Yedekleme yanıt modeli."""
    backup_id: str
    status: str
    path: str

class RestoreRequest(BaseModel):
    """Geri yükleme isteği modeli."""
    backup_path: str
    include_vector_store: bool = True
    include_agents: bool = True
    include_connectors: bool = True

class RestoreResponse(BaseModel):
    """Geri yükleme yanıt modeli."""
    restore_id: str
    status: str

@router.get("/stats", response_model=SystemStatsResponse, dependencies=[Depends(verify_token)])
async def get_system_stats(
    vector_store=Depends(get_vector_store),
    agent_manager=Depends(get_agent_manager),
    connector_registry=Depends(get_connector_registry)
):
    """
    Sistem istatistiklerini döndürür.
    """
    try:
        # Vector Store istatistikleri
        vector_stats = {}
        if vector_store:
            # Temel istatistikleri al
            vector_stats = vector_store.get_stats()
            
            # Belge sayıları
            from ModularMind.API.services.retrieval.models import get_unique_document_ids
            vector_stats["unique_document_count"] = len(get_unique_document_ids(vector_store))
        
        # Ajan istatistikleri
        agent_stats = {}
        if agent_manager:
            # Toplam ajan sayısı
            agent_stats["total_agents"] = len(agent_manager.agents)
            
            # Etkin ajanlar
            agent_stats["enabled_agents"] = len([a for a in agent_manager.agents.values() if a.enabled])
            
            # Çalışan ajanlar
            agent_stats["running_agents"] = len(agent_manager.running_agents)
            
            # Ajan tipleri
            agent_types = {}
            for agent in agent_manager.agents.values():
                agent_type = agent.agent_type
                agent_types[agent_type] = agent_types.get(agent_type, 0) + 1
            
            agent_stats["agent_types"] = agent_types
            
            # Son çalışma sonuçları
            agent_stats["successful_runs"] = len([r for r in agent_manager.last_results.values() if r.success])
            agent_stats["failed_runs"] = len([r for r in agent_manager.last_results.values() if not r.success])
        
        # Konnektör istatistikleri
        connector_stats = {}
        if connector_registry:
            # Toplam konnektör sayısı
            connector_stats["total_connectors"] = len(connector_registry.connectors)
            
            # Aktif konnektörler
            connector_stats["active_connectors"] = len(connector_registry.active_connectors)
            
            # Konnektör tipleri
            connector_types = {}
            for connector in connector_registry.connectors.values():
                connector_type = connector.connector_type
                connector_types[connector_type] = connector_types.get(connector_type, 0) + 1
            
            connector_stats["connector_types"] = connector_types
        
        return {
            "vector_store": vector_stats,
            "agents": agent_stats,
            "connectors": connector_stats
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/backup", response_model=BackupResponse, dependencies=[Depends(verify_token)])
async def create_backup(
    request: BackupRequest,
    background_tasks: BackgroundTasks,
    vector_store=Depends(get_vector_store),
    agent_manager=Depends(get_agent_manager),
    connector_registry=Depends(get_connector_registry)
):
    """
    Sistem yedeklemesi oluşturur.
    """
    try:
        # Yedek ID'si
        backup_id = f"backup_{uuid.uuid4().hex}"
        
        # Yedekleme dizini
        backup_path = request.backup_path or "./backups"
        os.makedirs(backup_path, exist_ok=True)
        
        # Yedek alt dizini
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.join(backup_path, f"{timestamp}_{backup_id}")
        os.makedirs(backup_dir, exist_ok=True)
        
        # Yedekleme işlemi
        def perform_backup():
            try:
                # Vector Store yedekle
                if request.include_vector_store and vector_store:
                    vector_dir = os.path.join(backup_dir, "vector_store")
                    os.makedirs(vector_dir, exist_ok=True)
                    
                    # Vector Store yapılandırmasını kaydet
                    with open(os.path.join(vector_dir, "config.json"), "w") as f:
                        json.dump(vector_store.config.to_dict(), f, indent=2)
                    
                    # Vector Store verilerini kopyala
                    if vector_store.config.storage_path and os.path.exists(vector_store.config.storage_path):
                        shutil.copytree(
                            vector_store.config.storage_path,
                            os.path.join(vector_dir, "data"),
                            dirs_exist_ok=True
                        )
                
                # Ajan yapılandırmalarını yedekle
                if request.include_agents and agent_manager:
                    agent_dir = os.path.join(backup_dir, "agents")
                    os.makedirs(agent_dir, exist_ok=True)
                    
                    # Her ajan için yapılandırma dosyası oluştur
                    for agent_id, agent in agent_manager.agents.items():
                        with open(os.path.join(agent_dir, f"{agent_id}.json"), "w") as f:
                            json.dump(agent.to_dict(), f, indent=2)
                
                # Konnektör yapılandırmalarını yedekle
                if request.include_connectors and connector_registry:
                    connector_dir = os.path.join(backup_dir, "connectors")
                    os.makedirs(connector_dir, exist_ok=True)
                    
                    # Her konnektör için yapılandırma dosyası oluştur
                    for connector_id, connector in connector_registry.connectors.items():
                        with open(os.path.join(connector_dir, f"{connector_id}.json"), "w") as f:
                            json.dump(connector.to_dict(), f, indent=2)
                
                # Yedekleme bilgisini kaydet
                metadata = {
                    "backup_id": backup_id,
                    "timestamp": timestamp,
                    "include_vector_store": request.include_vector_store,
                    "include_agents": request.include_agents,
                    "include_connectors": request.include_connectors,
                    "completed": True
                }
                
                with open(os.path.join(backup_dir, "metadata.json"), "w") as f:
                    json.dump(metadata, f, indent=2)
                    
            except Exception as e:
                # Hata durumunda metadata güncelle
                metadata = {
                    "backup_id": backup_id,
                    "timestamp": timestamp,
                    "error": str(e),
                    "completed": False
                }
                
                with open(os.path.join(backup_dir, "metadata.json"), "w") as f:
                    json.dump(metadata, f, indent=2)
        
        # Arka planda yedekleme işlemini başlat
        background_tasks.add_task(perform_backup)
        
        return {
            "backup_id": backup_id,
            "status": "started",
            "path": backup_dir
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/restore", response_model=RestoreResponse, dependencies=[Depends(verify_token)])
async def restore_backup(
    request: RestoreRequest,
    background_tasks: BackgroundTasks,
    vector_store=Depends(get_vector_store),
    agent_manager=Depends(get_agent_manager),
    connector_registry=Depends(get_connector_registry)
):
    """
    Sistem yedeğini geri yükler.
    """
    try:
        # Yedek dizinini kontrol et
        backup_path = request.backup_path
        if not os.path.exists(backup_path) or not os.path.isdir(backup_path):
            raise HTTPException(status_code=404, detail=f"Yedek dizini bulunamadı: {backup_path}")
        
        # Metadata dosyasını kontrol et
        metadata_path = os.path.join(backup_path, "metadata.json")
        if not os.path.exists(metadata_path):
            raise HTTPException(status_code=400, detail="Geçersiz yedek dizini: metadata.json bulunamadı")
        
        # Metadata oku
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
        
        # Yedek tamamlanmış mı kontrol et
        if not metadata.get("completed", False):
            raise HTTPException(status_code=400, detail="Tamamlanmamış yedek geri yüklenemez")
        
        # Restore ID
        restore_id = f"restore_{uuid.uuid4().hex}"
        
        # Geri yükleme işlemi
        def perform_restore():
            try:
                # Vector Store geri yükle
                if request.include_vector_store and vector_store and os.path.exists(os.path.join(backup_path, "vector_store")):
                    # Vector Store'u kapat
                    vector_store.close()
                    
                    # Yapılandırmayı yükle
                    config_path = os.path.join(backup_path, "vector_store", "config.json")
                    if os.path.exists(config_path):
                        with open(config_path, "r") as f:
                            config_data = json.load(f)
                        
                        # Yapılandırmayı güncelle
                        from ModularMind.API.services.retrieval.vector_models import VectorStoreConfig
                        new_config = VectorStoreConfig.from_dict(config_data)
                        vector_store.config = new_config
                    
                    # Vector Store verilerini geri yükle
                    data_path = os.path.join(backup_path, "vector_store", "data")
                    if os.path.exists(data_path) and vector_store.config.storage_path:
                        # Mevcut verileri temizle
                        if os.path.exists(vector_store.config.storage_path):
                            shutil.rmtree(vector_store.config.storage_path)
                        
                        # Verileri kopyala
                        shutil.copytree(
                            data_path,
                            vector_store.config.storage_path,
                            dirs_exist_ok=True
                        )
                    
                    # Vector Store'u yeniden yükle
                    vector_store.load()
                
                # Ajan yapılandırmalarını geri yükle
                if request.include_agents and agent_manager and os.path.exists(os.path.join(backup_path, "agents")):
                    agent_dir = os.path.join(backup_path, "agents")
                    
                    # Mevcut ajanları temizle
                    for agent_id in list(agent_manager.agents.keys()):
                        agent_manager.delete_agent(agent_id)
                    
                    # Ajanları yükle
                    for filename in os.listdir(agent_dir):
                        if filename.endswith(".json"):
                            with open(os.path.join(agent_dir, filename), "r") as f:
                                agent_data = json.load(f)
                            
                            # Ajan yapılandırmasını oluştur
                            from ModularMind.API.services.data.source_agent_models import AgentConfig
                            agent_config = AgentConfig.from_dict(agent_data)
                            
                            # Ajanı ekle
                            agent_manager.add_agent(agent_config)
                
                # Konnektör yapılandırmalarını geri yükle
                if request.include_connectors and connector_registry and os.path.exists(os.path.join(backup_path, "connectors")):
                    connector_dir = os.path.join(backup_path, "connectors")
                    
                    # Mevcut konnektörleri temizle
                    for connector_id in list(connector_registry.connectors.keys()):
                        connector_registry.delete_connector(connector_id)
                    
                    # Konnektörleri yükle
                    for filename in os.listdir(connector_dir):
                        if filename.endswith(".json"):
                            with open(os.path.join(connector_dir, filename), "r") as f:
                                connector_data = json.load(f)
                            
                            # Konnektör yapılandırmasını oluştur
                            from ModularMind.API.services.data.connector_models import ConnectorConfig
                            connector_config = ConnectorConfig.from_dict(connector_data)
                            
                            # Konnektörü ekle
                            connector_registry.register_connector(connector_config)
                
                # Geri yükleme bilgisini kaydet
                restore_metadata = {
                    "restore_id": restore_id,
                    "backup_id": metadata.get("backup_id"),
                    "timestamp": datetime.datetime.now().strftime("%Y%m%d_%H%M%S"),
                    "include_vector_store": request.include_vector_store,
                    "include_agents": request.include_agents,
                    "include_connectors": request.include_connectors,
                    "completed": True
                }
                
                with open(os.path.join(backup_path, "restore.json"), "w") as f:
                    json.dump(restore_metadata, f, indent=2)
                    
            except Exception as e:
                # Hata durumunda metadata güncelle
                restore_metadata = {
                    "restore_id": restore_id,
                    "backup_id": metadata.get("backup_id"),
                    "timestamp": datetime.datetime.now().strftime("%Y%m%d_%H%M%S"),
                    "error": str(e),
                    "completed": False
                }
                
                with open(os.path.join(backup_path, "restore.json"), "w") as f:
                    json.dump(restore_metadata, f, indent=2)
        
        # Arka planda geri yükleme işlemini başlat
        background_tasks.add_task(perform_restore)
        
        return {
            "restore_id": restore_id,
            "status": "started"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rebuild_indices", dependencies=[Depends(verify_token)])
async def rebuild_indices(
    background_tasks: BackgroundTasks,
    vector_store=Depends(get_vector_store)
):
    """
    Vector Store indekslerini yeniden oluşturur.
    """
    try:
        if not vector_store:
            raise HTTPException(status_code=404, detail="Vector Store bulunamadı")
        
        # Arka planda indekslerini yeniden oluştur
        def rebuild_vector_indices():
            try:
                from ModularMind.API.services.retrieval.indices import _rebuild_index
                _rebuild_index(vector_store)
                
                # İndeks oluşturulduktan sonra kaydet
                vector_store.save()
                
            except Exception as e:
                logger.error(f"İndeks yeniden oluşturma hatası: {str(e)}")
        
        # Arka planda çalıştır
        background_tasks.add_task(rebuild_vector_indices)
        
        return {"status": "started", "message": "İndeksler yeniden oluşturuluyor"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reset", dependencies=[Depends(verify_token)])
async def reset_system(
    background_tasks: BackgroundTasks,
    include_vector_store: bool = True,
    include_agents: bool = True,
    include_connectors: bool = True,
    vector_store=Depends(get_vector_store),
    agent_manager=Depends(get_agent_manager),
    connector_registry=Depends(get_connector_registry)
):
    """
    Sistemi sıfırlar.
    """
    try:
        # Arka planda sıfırlama işlemi
        def perform_reset():
            try:
                # Vector Store sıfırla
                if include_vector_store and vector_store:
                    # Verileri temizle
                    vector_store.clear()
                    
                    # Değişiklikleri kaydet
                    vector_store.save()
                
                # Ajanları sıfırla
                if include_agents and agent_manager:
                    # Tüm ajanları sil
                    for agent_id in list(agent_manager.agents.keys()):
                        agent_manager.delete_agent(agent_id)
                
                # Konnektörleri sıfırla
                if include_connectors and connector_registry:
                    # Tüm konnektörleri sil
                    for connector_id in list(connector_registry.connectors.keys()):
                        connector_registry.delete_connector(connector_id)
                        
            except Exception as e:
                logger.error(f"Sistem sıfırlama hatası: {str(e)}")
        
        # Arka planda çalıştır
        background_tasks.add_task(perform_reset)
        
        return {"status": "started", "message": "Sistem sıfırlanıyor"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))