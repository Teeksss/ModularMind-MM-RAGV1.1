from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Any, Optional
from app.core.auth import get_current_user, get_current_superuser
from app.schemas.metrics import (
    SystemMetrics,
    RAGMetrics,
    AgentMetrics,
    UserMetrics
)
from app.services.metrics_service import MetricsService
from app.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.get("/system", response_model=SystemMetrics)
async def get_system_metrics(
    current_user = Depends(get_current_superuser),
    metrics_service: MetricsService = Depends()
) -> Any:
    """
    Get system metrics (admin only)
    """
    try:
        metrics = await metrics_service.get_system_metrics()
        return metrics
    except Exception as e:
        logger.error(f"Failed to get system metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/rag", response_model=RAGMetrics)
async def get_rag_metrics(
    time_range: Optional[str] = Query("day", regex="^(hour|day|week|month)$"),
    current_user = Depends(get_current_user),
    metrics_service: MetricsService = Depends()
) -> Any:
    """
    Get RAG metrics
    """
    try:
        metrics = await metrics_service.get_rag_metrics(
            user_id=current_user.id,
            time_range=time_range
        )
        return metrics
    except Exception as e:
        logger.error(f"Failed to get RAG metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/agents", response_model=AgentMetrics)
async def get_agent_metrics(
    time_range: Optional[str] = Query("day", regex="^(hour|day|week|month)$"),
    agent_id: Optional[str] = None,
    current_user = Depends(get_current_user),
    metrics_service: MetricsService = Depends()
) -> Any:
    """
    Get agent metrics
    """
    try:
        metrics = await metrics_service.get_agent_metrics(
            user_id=current_user.id,
            agent_id=agent_id,
            time_range=time_range
        )
        return metrics
    except Exception as e:
        logger.error(f"Failed to get agent metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/users", response_model=UserMetrics)
async def get_user_metrics(
    current_user = Depends(get_current_superuser),
    metrics_service: MetricsService = Depends()
) -> Any:
    """
    Get user metrics (admin only)
    """
    try:
        metrics = await metrics_service.get_user_metrics()
        return metrics
    except Exception as e:
        logger.error(f"Failed to get user metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )