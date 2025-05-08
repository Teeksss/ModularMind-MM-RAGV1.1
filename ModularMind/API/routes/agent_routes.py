"""
Ajan API rotaları.
"""

from fastapi import APIRouter, Depends, HTTPException, Path, Query, BackgroundTasks
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from ModularMind.API.main import get_agent_manager, verify_token
from ModularMind.API.services.data.source_agent_models import AgentType

router = APIRouter()

class AgentConfigRequest(BaseModel):
    """Ajan yapılandırma isteği modeli."""
    name: str
    agent_type: str
    description: Optional[str] = ""
    source_url: Optional[str] = None
    credentials: Optional[Dict[str, Any]] = None
    schedule: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    options: Optional[Dict[str, Any]] = None
    metadata_mapping: Optional[Dict[str, str]] = None
    max_items: Optional[int] = None

class AgentUpdateRequest(BaseModel):
    """Ajan güncelleme isteği modeli."""
    name: Optional[str] = None
    description: Optional[str] = None
    source_url: Optional[str] = None
    credentials: Optional[Dict[str, Any]] = None
    schedule: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    options: Optional[Dict[str, Any]] = None
    metadata_mapping: Optional[Dict[str, str]] = None
    enabled: Optional[bool] = None
    max_items: Optional[int] = None

class AgentResponse(BaseModel):
    """Ajan yanıt modeli."""
    agent_id: str
    name: str
    agent_type: str
    description: str
    enabled: bool
    status: str
    schedule: Optional[str]
    last_run: Optional[float]

class AgentsListResponse(BaseModel):
    """Ajanlar listesi yanıt modeli."""
    agents: List[AgentResponse]

class AgentDetailResponse(BaseModel):
    """Ajan detay yanıt modeli."""
    agent_id: str
    name: str
    agent_type: str
    description: str
    source_url: Optional[str]
    schedule: Optional[str]
    filters: Dict[str, Any]
    options: Dict[str, Any]
    metadata_mapping: Dict[str, str]
    enabled: bool
    status: str
    last_run: Optional[float]
    error_count: int
    max_items: int

class AgentRunResponse(BaseModel):
    """Ajan çalıştırma yanıt modeli."""
    job_id: str
    agent_id: str
    status: str

class AgentResultResponse(BaseModel):
    """Ajan sonuç yanıt modeli."""
    agent_id: str
    success: bool
    item_count: int
    start_time: Optional[float]
    end_time: Optional[float]
    duration: Optional[float]
    error_message: Optional[str]
    metadata: Dict[str, Any]

@router.post("/", response_model=AgentResponse, dependencies=[Depends(verify_token)])
async def create_agent(
    request: AgentConfigRequest,
    agent_manager=Depends(get_agent_manager)
):
    """
    Yeni bir ajan kaydeder.
    """
    try:
        # AgentType doğrula
        try:
            agent_type = AgentType(request.agent_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Geçersiz ajan tipi: {request.agent_type}. Geçerli tipler: {[t.value for t in AgentType]}"
            )
        
        # Yapılandırma oluştur
        from ModularMind.API.services.data.source_agent_models import AgentConfig
        
        config = AgentConfig(
            agent_id="",  # Otomatik oluşturulacak
            name=request.name,
            agent_type=agent_type,
            description=request.description or "",
            source_url=request.source_url,
            credentials=request.credentials or {},
            schedule=request.schedule,
            filters=request.filters or {},
            options=request.options or {},
            metadata_mapping=request.metadata_mapping or {},
            max_items=request.max_items or 100
        )
        
        # Ajanı kaydet
        agent_id = agent_manager.add_agent(config)
        
        # Ajan bilgilerini döndür
        agent = agent_manager.get_agent(agent_id)
        status = agent_manager._get_agent_status(agent_id)
        
        return {
            "agent_id": agent_id,
            "name": agent.name,
            "agent_type": agent.agent_type,
            "description": agent.description,
            "enabled": agent.enabled,
            "status": status,
            "schedule": agent.schedule,
            "last_run": agent.last_run
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=AgentsListResponse, dependencies=[Depends(verify_token)])
async def list_agents(agent_manager=Depends(get_agent_manager)):
    """
    Tüm ajanları listeler.
    """
    try:
        agents = agent_manager.list_agents()
        
        return {"agents": agents}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{agent_id}", response_model=AgentDetailResponse, dependencies=[Depends(verify_token)])
async def get_agent(
    agent_id: str = Path(..., description="Ajan ID"),
    agent_manager=Depends(get_agent_manager)
):
    """
    Ajan detaylarını döndürür.
    """
    try:
        agent = agent_manager.get_agent(agent_id)
        
        if not agent:
            raise HTTPException(status_code=404, detail=f"Ajan bulunamadı: {agent_id}")
        
        status_info = agent_manager.get_agent_status(agent_id)
        
        return {
            "agent_id": agent.agent_id,
            "name": agent.name,
            "agent_type": agent.agent_type,
            "description": agent.description,
            "source_url": agent.source_url,
            "schedule": agent.schedule,
            "filters": agent.filters,
            "options": agent.options,
            "metadata_mapping": agent.metadata_mapping,
            "enabled": agent.enabled,
            "status": status_info["status"],
            "last_run": agent.last_run,
            "error_count": agent.error_count,
            "max_items": agent.max_items
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{agent_id}", response_model=AgentResponse, dependencies=[Depends(verify_token)])
async def update_agent(
    request: AgentUpdateRequest,
    agent_id: str = Path(..., description="Ajan ID"),
    agent_manager=Depends(get_agent_manager)
):
    """
    Ajan bilgilerini günceller.
    """
    try:
        # Ajan varlığını kontrol et
        if not agent_manager.get_agent(agent_id):
            raise HTTPException(status_code=404, detail=f"Ajan bulunamadı: {agent_id}")
        
        # Güncellenecek alanları filtrele
        update_data = {}
        
        for field, value in request.dict(exclude_unset=True).items():
            update_data[field] = value
        
        # Ajanı güncelle
        agent = agent_manager.update_agent(agent_id, update_data)
        
        if not agent:
            raise HTTPException(status_code=500, detail="Ajan güncellenemedi")
        
        status = agent_manager._get_agent_status(agent_id)
        
        return {
            "agent_id": agent.agent_id,
            "name": agent.name,
            "agent_type": agent.agent_type,
            "description": agent.description,
            "enabled": agent.enabled,
            "status": status,
            "schedule": agent.schedule,
            "last_run": agent.last_run
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{agent_id}", dependencies=[Depends(verify_token)])
async def delete_agent(
    agent_id: str = Path(..., description="Ajan ID"),
    agent_manager=Depends(get_agent_manager)
):
    """
    Ajanı siler.
    """
    try:
        # Ajan varlığını kontrol et
        if not agent_manager.get_agent(agent_id):
            raise HTTPException(status_code=404, detail=f"Ajan bulunamadı: {agent_id}")
        
        # Ajanı sil
        success = agent_manager.delete_agent(agent_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="Ajan silinemedi")
        
        return {"status": "success", "message": f"Ajan silindi: {agent_id}"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{agent_id}/run", response_model=AgentRunResponse, dependencies=[Depends(verify_token)])
async def run_agent(
    background_tasks: BackgroundTasks,
    agent_id: str = Path(..., description="Ajan ID"),
    sync: bool = Query(False, description="Senkron çalıştırma"),
    agent_manager=Depends(get_agent_manager)
):
    """
    Ajanı çalıştırır.
    """
    try:
        # Ajan varlığını kontrol et
        if not agent_manager.get_agent(agent_id):
            raise HTTPException(status_code=404, detail=f"Ajan bulunamadı: {agent_id}")
        
        # Durum kontrolü
        status_info = agent_manager.get_agent_status(agent_id)
        
        if status_info["status"] == "running":
            return {
                "job_id": "already_running",
                "agent_id": agent_id,
                "status": "running"
            }
        
        # Asenkron çalıştır
        if not sync:
            job_id = agent_manager.run_agent(agent_id, sync=False)
            
            if job_id:
                return {
                    "job_id": job_id,
                    "agent_id": agent_id,
                    "status": "started"
                }
            else:
                raise HTTPException(status_code=500, detail="Ajan başlatılamadı")
        
        # Senkron çalıştır
        else:
            job_id = agent_manager.run_agent(agent_id, sync=True)
            
            return {
                "job_id": job_id,
                "agent_id": agent_id,
                "status": "completed"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{agent_id}/status", dependencies=[Depends(verify_token)])
async def agent_status(
    agent_id: str = Path(..., description="Ajan ID"),
    agent_manager=Depends(get_agent_manager)
):
    """
    Ajan durumunu döndürür.
    """
    try:
        # Ajan varlığını kontrol et
        if not agent_manager.get_agent(agent_id):
            raise HTTPException(status_code=404, detail=f"Ajan bulunamadı: {agent_id}")
        
        # Durum bilgilerini al
        status_info = agent_manager.get_agent_status(agent_id)
        
        return status_info
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{agent_id}/result", response_model=AgentResultResponse, dependencies=[Depends(verify_token)])
async def agent_result(
    agent_id: str = Path(..., description="Ajan ID"),
    agent_manager=Depends(get_agent_manager)
):
    """
    Ajan sonucunu döndürür.
    """
    try:
        # Ajan varlığını kontrol et
        if not agent_manager.get_agent(agent_id):
            raise HTTPException(status_code=404, detail=f"Ajan bulunamadı: {agent_id}")
        
        # Sonuç bilgilerini al
        result = agent_manager.get_agent_result(agent_id)
        
        if not result:
            raise HTTPException(status_code=404, detail=f"Ajan sonucu bulunamadı: {agent_id}")
        
        return {
            "agent_id": result["agent_id"],
            "success": result["success"],
            "item_count": result["item_count"],
            "start_time": result["start_time"],
            "end_time": result["end_time"],
            "duration": result.get("duration"),
            "error_message": result["error_message"],
            "metadata": result["metadata"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))