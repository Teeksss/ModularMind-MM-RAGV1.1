"""
ModularMind API için izleme endpointleri.
Kaynak kullanımı, hata izleme ve sistem metrikleri için API'ler sağlar.
"""

import os
import time
import logging
import json
from datetime import datetime, timedelta
import random
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query, Path, status
from pydantic import BaseModel

from ModularMind.API.models.user import User, UserRole
from ModularMind.API.core.auth import get_current_active_user
from ModularMind.API.core.resource_manager import ResourceManager
from ModularMind.API.core.advanced_cache import AdvancedCacheManager
from ModularMind.API.services.log_service import LogService

router = APIRouter(prefix="/admin/monitoring", tags=["monitoring"])

# Sadece admin erişimi için bağımlılık
def check_admin_access(current_user: User = Depends(get_current_active_user)):
    """Admin erişimi kontrol eden bağımlılık."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu endpoint için admin erişimi gereklidir"
        )
    return current_user

# Sağlık kontrolü
@router.get("/health")
async def get_health(current_user: User = Depends(check_admin_access)):
    """
    Sistem sağlık durumunu döndürür.
    Kaynak kullanımı, önbellek durumu ve diğer sistem bilgilerini içerir.
    """
    # Uygulama başlangıç zamanı
    start_time = float(os.getenv("APP_START_TIME", time.time()))
    uptime = int(time.time() - start_time)
    
    # Kaynak kullanım bilgilerini al
    resource_manager = ResourceManager()
    resources = resource_manager.get_system_resources()
    
    # Önbellek istatistiklerini al
    cache_manager = AdvancedCacheManager()
    cache_stats = cache_manager.stats()
    
    return {
        "status": "ok",
        "version": os.getenv("APP_VERSION", "1.0.0"),
        "environment": os.getenv("ENVIRONMENT", "development"),
        "uptime_seconds": uptime,
        "resources": resources,
        "cache": cache_stats,
        "timestamp": time.time()
    }

# Metrikler
@router.get("/metrics")
async def get_metrics(
    time_range: str = Query("1h", regex=r"^(1h|3h|12h|24h|7d)$"),
    current_user: User = Depends(check_admin_access)
):
    """
    Sistem metriklerini belirli bir zaman aralığı için döndürür.
    
    Args:
        time_range: Zaman aralığı (1h, 3h, 12h, 24h, 7d)
    """
    # Zaman aralığını hesapla
    now = datetime.utcnow()
    if time_range == "1h":
        start_time = now - timedelta(hours=1)
        interval = "1m"  # 1 dakika
    elif time_range == "3h":
        start_time = now - timedelta(hours=3)
        interval = "5m"  # 5 dakika
    elif time_range == "12h":
        start_time = now - timedelta(hours=12)
        interval = "15m"  # 15 dakika
    elif time_range == "24h":
        start_time = now - timedelta(hours=24)
        interval = "30m"  # 30 dakika
    elif time_range == "7d":
        start_time = now - timedelta(days=7)
        interval = "2h"  # 2 saat
    else:
        start_time = now - timedelta(hours=1)
        interval = "1m"
    
    # Şu anda Prometheus gibi bir gerçek metrik sistemi olmadığı için
    # Demo verileri oluştur (Gerçek uygulamada burada Prometheus'tan veriler çekilecek)
    
    # Zaman etiketleri oluştur
    time_labels = []
    current = start_time
    while current <= now:
        time_labels.append(current.strftime("%H:%M"))
        
        # Aralığa göre artır
        if interval == "1m":
            current += timedelta(minutes=1)
        elif interval == "5m":
            current += timedelta(minutes=5)
        elif interval == "15m":
            current += timedelta(minutes=15)
        elif interval == "30m":
            current += timedelta(minutes=30)
        elif interval == "2h":
            current += timedelta(hours=2)
    
    # HTTP istek metrikleri
    success_requests = []
    error_requests = []
    for _ in range(len(time_labels)):
        success_requests.append(random.randint(50, 200))
        error_requests.append(random.randint(0, 10))
    
    # Kaynak kullanım metrikleri
    cpu_usage = []
    memory_usage = []
    for _ in range(len(time_labels)):
        cpu_usage.append(random.randint(20, 80))
        memory_usage.append(random.randint(40, 85))
    
    # Önbellek performans metrikleri
    cache_hit_ratio = []
    for _ in range(len(time_labels)):
        cache_hit_ratio.append(random.randint(60, 95))
    
    # Endpoint performans metrikleri
    endpoints = ["/api/v1/chat", "/api/v1/search", "/api/v1/documents", "/api/v1/embeddings", "/api/v1/auth"]
    endpoint_response_times = []
    for _ in endpoints:
        endpoint_response_times.append(random.randint(50, 500))
    
    # Model kullanım metrikleri
    models = ["gpt-4", "gpt-3.5-turbo", "text-embedding-3-large", "custom-model"]
    model_counts = []
    for _ in models:
        model_counts.append(random.randint(100, 1000))
    
    # Tüm metrikleri döndür
    return {
        "http_requests": {
            "labels": time_labels,
            "success": success_requests,
            "error": error_requests
        },
        "resources": {
            "labels": time_labels,
            "cpu": cpu_usage,
            "memory": memory_usage
        },
        "cache": {
            "labels": time_labels,
            "hit_ratio": cache_hit_ratio
        },
        "endpoints": {
            "labels": endpoints,
            "response_times": endpoint_response_times
        },
        "models": {
            "labels": models,
            "request_counts": model_counts
        }
    }

# Log kayıtlarını al
@router.get("/logs")
async def get_logs(
    level: str = Query("ERROR", regex=r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$"),
    limit: int = Query(100, ge=1, le=1000),
    start_time: Optional[float] = Query(None),
    end_time: Optional[float] = Query(None),
    module: Optional[str] = Query(None),
    current_user: User = Depends(check_admin_access)
):
    """
    Log kayıtlarını filtrelere göre döndürür.
    
    Args:
        level: Log seviyesi (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        limit: Maksimum döndürülecek log sayısı
        start_time: Başlangıç zamanı (Unix timestamp)
        end_time: Bitiş zamanı (Unix timestamp)
        module: Filtrelenecek modül adı
    """
    # Log servisini başlat
    log_service = LogService()
    
    # Logları getir
    logs = log_service.get_logs(
        level=level,
        limit=limit,
        start_time=start_time,
        end_time=end_time,
        module=module
    )
    
    return {
        "logs": logs,
        "count": len(logs),
        "filters": {
            "level": level,
            "limit": limit,
            "start_time": start_time,
            "end_time": end_time,
            "module": module
        }
    }

# WebSocket bağlantısı
@router.websocket("/ws")
async def metrics_websocket(websocket: WebSocket):
    """
    Gerçek zamanlı metrik güncellemeleri için WebSocket bağlantısı.
    """
    await websocket.accept()
    
    try:
        # Kullanıcı doğrulama
        # Not: Gerçek uygulamada WebSocket üzerinden de kimlik doğrulama yapılmalıdır
        
        # Her 5 saniyede bir metrik güncellemeleri gönder
        while True:
            # Anlık kaynak kullanımını al
            resource_manager = ResourceManager()
            resources = resource_manager.get_system_resources()
            
            # Anlık önbellek istatistiklerini al
            cache_manager = AdvancedCacheManager()
            cache_stats = cache_manager.stats()
            
            # Metrikleri hazırla
            metrics = {
                "timestamp": time.time(),
                "resources": {
                    "cpu": resources["cpu"]["percent"],
                    "memory": resources["memory"]["percent"],
                    "disk": resources["disk"]["percent"]
                },
                "cache": {
                    "memory_size": cache_stats["memory_cache"]["size"],
                    "hit_ratio": random.randint(60, 95)  # Gerçek veri için bu değiştirilmelidir
                },
                "requests": {
                    "active": random.randint(1, 50),
                    "per_second": random.randint(1, 20)
                }
            }
            
            # WebSocket üzerinden metrikleri gönder
            await websocket.send_json(metrics)
            
            # 5 saniye bekle
            await asyncio.sleep(5)
            
    except WebSocketDisconnect:
        # Bağlantı kesildiğinde temizlik yap
        pass

# Önbellek istatistikleri
@router.get("/cache")
async def get_cache_stats(current_user: User = Depends(check_admin_access)):
    """
    Önbellek istatistiklerini döndürür.
    """
    cache_manager = AdvancedCacheManager()
    stats = cache_manager.stats()
    
    return stats

# Önbelleği temizle
@router.post("/cache/clear")
async def clear_cache(
    cache_type: Optional[str] = None,
    current_user: User = Depends(check_admin_access)
):
    """
    Önbelleği temizler.
    
    Args:
        cache_type: Temizlenecek önbellek türü (memory, redis, all)
    """
    cache_manager = AdvancedCacheManager()
    
    result = cache_manager.clear_all()
    
    return {
        "success": result,
        "message": "Önbellek başarıyla temizlendi" if result else "Önbellek temizlenirken hata oluştu",
        "cache_type": cache_type or "all"
    }