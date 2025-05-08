"""
Konnektör API rotaları.
"""

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from ModularMind.API.main import get_connector_registry, verify_token
from ModularMind.API.services.data.connector_models import ConnectorType

router = APIRouter()

class ConnectorConfigRequest(BaseModel):
    """Konnektör yapılandırma isteği modeli."""
    name: str
    connector_type: str
    description: Optional[str] = ""
    credentials: Optional[Dict[str, Any]] = None
    connection_string: Optional[str] = None
    options: Optional[Dict[str, Any]] = None
    module_path: Optional[str] = None
    class_name: Optional[str] = None

class ConnectorUpdateRequest(BaseModel):
    """Konnektör güncelleme isteği modeli."""
    name: Optional[str] = None
    description: Optional[str] = None
    credentials: Optional[Dict[str, Any]] = None
    connection_string: Optional[str] = None
    options: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None
    module_path: Optional[str] = None
    class_name: Optional[str] = None

class ConnectorQueryRequest(BaseModel):
    """Konnektör sorgu isteği modeli."""
    query: str
    params: Optional[Dict[str, Any]] = None

class ConnectorResponse(BaseModel):
    """Konnektör yanıt modeli."""
    connector_id: str
    name: str
    connector_type: str
    description: str
    enabled: bool
    is_connected: bool

class ConnectorsListResponse(BaseModel):
    """Konnektörler listesi yanıt modeli."""
    connectors: List[ConnectorResponse]

class ConnectorDetailResponse(BaseModel):
    """Konnektör detay yanıt modeli."""
    connector_id: str
    name: str
    connector_type: str
    description: str
    connection_string: Optional[str]
    options: Dict[str, Any]
    enabled: bool
    is_connected: bool
    module_path: Optional[str]
    class_name: Optional[str]

class ConnectorQueryResponse(BaseModel):
    """Konnektör sorgu yanıt modeli."""
    results: List[Dict[str, Any]]
    count: int

class ConnectorTestResponse(BaseModel):
    """Konnektör test yanıt modeli."""
    success: bool
    message: str

class ConnectorMetadataResponse(BaseModel):
    """Konnektör metadata yanıt modeli."""
    metadata: Dict[str, Any]

@router.post("/", response_model=ConnectorResponse, dependencies=[Depends(verify_token)])
async def create_connector(
    request: ConnectorConfigRequest,
    connector_registry=Depends(get_connector_registry)
):
    """
    Yeni bir konnektör kaydeder.
    """
    try:
        # ConnectorType doğrula
        try:
            connector_type = ConnectorType(request.connector_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Geçersiz konnektör tipi: {request.connector_type}. Geçerli tipler: {[t.value for t in ConnectorType]}"
            )
        
        # Yapılandırma oluştur
        from ModularMind.API.services.data.connector_models import ConnectorConfig
        
        config = ConnectorConfig(
            connector_id="",  # Otomatik oluşturulacak
            name=request.name,
            connector_type=connector_type,
            description=request.description or "",
            credentials=request.credentials or {},
            connection_string=request.connection_string,
            options=request.options or {},
            module_path=request.module_path,
            class_name=request.class_name
        )
        
        # Konnektörü kaydet
        connector_id = connector_registry.register_connector(config)
        
        # Konnektör bilgilerini döndür
        connector = connector_registry.get_connector(connector_id)
        
        return {
            "connector_id": connector_id,
            "name": connector.name,
            "connector_type": connector.connector_type,
            "description": connector.description,
            "enabled": connector.enabled,
            "is_connected": False
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=ConnectorsListResponse, dependencies=[Depends(verify_token)])
async def list_connectors(connector_registry=Depends(get_connector_registry)):
    """
    Tüm konnektörleri listeler.
    """
    try:
        connectors = connector_registry.list_connectors()
        
        return {"connectors": connectors}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{connector_id}", response_model=ConnectorDetailResponse, dependencies=[Depends(verify_token)])
async def get_connector(
    connector_id: str = Path(..., description="Konnektör ID"),
    connector_registry=Depends(get_connector_registry)
):
    """
    Konnektör detaylarını döndürür.
    """
    try:
        connector = connector_registry.get_connector(connector_id)
        
        if not connector:
            raise HTTPException(status_code=404, detail=f"Konnektör bulunamadı: {connector_id}")
        
        is_connected = (
            connector_id in connector_registry.active_connectors and 
            connector_registry.active_connectors[connector_id].is_connected
        )
        
        return {
            "connector_id": connector.connector_id,
            "name": connector.name,
            "connector_type": connector.connector_type,
            "description": connector.description,
            "connection_string": connector.connection_string,
            "options": connector.options,
            "enabled": connector.enabled,
            "is_connected": is_connected,
            "module_path": connector.module_path,
            "class_name": connector.class_name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{connector_id}", response_model=ConnectorResponse, dependencies=[Depends(verify_token)])
async def update_connector(
    request: ConnectorUpdateRequest,
    connector_id: str = Path(..., description="Konnektör ID"),
    connector_registry=Depends(get_connector_registry)
):
    """
    Konnektör bilgilerini günceller.
    """
    try:
        # Konnektör varlığını kontrol et
        if not connector_registry.get_connector(connector_id):
            raise HTTPException(status_code=404, detail=f"Konnektör bulunamadı: {connector_id}")
        
        # Güncellenecek alanları filtrele
        update_data = {}
        
        for field, value in request.dict(exclude_unset=True).items():
            update_data[field] = value
        
        # Konnektörü güncelle
        connector = connector_registry.update_connector(connector_id, update_data)
        
        if not connector:
            raise HTTPException(status_code=500, detail="Konnektör güncellenemedi")
        
        is_connected = (
            connector_id in connector_registry.active_connectors and 
            connector_registry.active_connectors[connector_id].is_connected
        )
        
        return {
            "connector_id": connector.connector_id,
            "name": connector.name,
            "connector_type": connector.connector_type,
            "description": connector.description,
            "enabled": connector.enabled,
            "is_connected": is_connected
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{connector_id}", dependencies=[Depends(verify_token)])
async def delete_connector(
    connector_id: str = Path(..., description="Konnektör ID"),
    connector_registry=Depends(get_connector_registry)
):
    """
    Konnektörü siler.
    """
    try:
        # Konnektör varlığını kontrol et
        if not connector_registry.get_connector(connector_id):
            raise HTTPException(status_code=404, detail=f"Konnektör bulunamadı: {connector_id}")
        
        # Konnektörü sil
        success = connector_registry.delete_connector(connector_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="Konnektör silinemedi")
        
        return {"status": "success", "message": f"Konnektör silindi: {connector_id}"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{connector_id}/query", response_model=ConnectorQueryResponse, dependencies=[Depends(verify_token)])
async def execute_query(
    request: ConnectorQueryRequest,
    connector_id: str = Path(..., description="Konnektör ID"),
    connector_registry=Depends(get_connector_registry)
):
    """
    Konnektör sorgusu çalıştırır.
    """
    try:
        # Konnektör varlığını kontrol et
        if not connector_registry.get_connector(connector_id):
            raise HTTPException(status_code=404, detail=f"Konnektör bulunamadı: {connector_id}")
        
        # Sorguyu çalıştır
        results = connector_registry.execute_query(
            connector_id=connector_id,
            query=request.query,
            params=request.params
        )
        
        return {
            "results": results,
            "count": len(results)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{connector_id}/test", response_model=ConnectorTestResponse, dependencies=[Depends(verify_token)])
async def test_connection(
    connector_id: str = Path(..., description="Konnektör ID"),
    connector_registry=Depends(get_connector_registry)
):
    """
    Konnektör bağlantısını test eder.
    """
    try:
        # Konnektör varlığını kontrol et
        if not connector_registry.get_connector(connector_id):
            raise HTTPException(status_code=404, detail=f"Konnektör bulunamadı: {connector_id}")
        
        # Bağlantı testi yap
        success = connector_registry.test_connection(connector_id)
        
        if success:
            return {
                "success": True,
                "message": "Bağlantı başarılı"
            }
        else:
            return {
                "success": False,
                "message": "Bağlantı başarısız"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        return {
            "success": False,
            "message": f"Bağlantı hatası: {str(e)}"
        }

@router.get("/{connector_id}/metadata", response_model=ConnectorMetadataResponse, dependencies=[Depends(verify_token)])
async def get_metadata(
    connector_id: str = Path(..., description="Konnektör ID"),
    connector_registry=Depends(get_connector_registry)
):
    """
    Konnektör metadata bilgilerini döndürür.
    """
    try:
        # Konnektör varlığını kontrol et
        if not connector_registry.get_connector(connector_id):
            raise HTTPException(status_code=404, detail=f"Konnektör bulunamadı: {connector_id}")
        
        # Metadata bilgilerini al
        metadata = connector_registry.get_metadata(connector_id)
        
        return {"metadata": metadata}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))