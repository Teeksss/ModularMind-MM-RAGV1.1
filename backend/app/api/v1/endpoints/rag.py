from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Any, List, Optional
from app.core.auth import get_current_user
from app.schemas.rag import (
    RAGQuery,
    RAGResponse,
    RAGFeedback,
    RAGHistory,
    RAGStats
)
from app.services.rag_service import RAGService
from app.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

@router.post("/query", response_model=RAGResponse)
async def query(
    query: RAGQuery,
    current_user = Depends(get_current_user),
    rag_service: RAGService = Depends()
) -> Any:
    """
    Process a RAG query
    """
    try:
        result = await rag_service.process_query(
            query=query.query,
            options=query.options,
            user_id=current_user.id
        )
        return result
    except Exception as e:
        logger.error(f"RAG query failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/history", response_model=List[RAGHistory])
async def get_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user = Depends(get_current_user),
    rag_service: RAGService = Depends()
) -> Any:
    """
    Get RAG query history
    """
    try:
        history = await rag_service.get_history(
            user_id=current_user.id,
            skip=skip,
            limit=limit
        )
        return history
    except Exception as e:
        logger.error(f"Failed to get RAG history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/feedback/{query_id}", response_model=RAGFeedback)
async def submit_feedback(
    query_id: str,
    feedback: RAGFeedback,
    current_user = Depends(get_current_user),
    rag_service: RAGService = Depends()
) -> Any:
    """
    Submit feedback for a RAG query
    """
    try:
        result = await rag_service.submit_feedback(
            query_id=query_id,
            feedback=feedback,
            user_id=current_user.id
        )
        return result
    except Exception as e:
        logger.error(f"Failed to submit feedback: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/stats", response_model=RAGStats)
async def get_stats(
    time_range: Optional[str] = Query("day", regex="^(hour|day|week|month)$"),
    current_user = Depends(get_current_user),
    rag_service: RAGService = Depends()
) -> Any:
    """
    Get RAG statistics
    """
    try:
        stats = await rag_service.get_stats(
            user_id=current_user.id,
            time_range=time_range
        )
        return stats
    except Exception as e:
        logger.error(f"Failed to get RAG stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )