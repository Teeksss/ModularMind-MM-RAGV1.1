from fastapi import APIRouter, Depends, HTTPException, Query, Body
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
import asyncio
import time
import uuid
from datetime import datetime

from app.models.query import (
    QueryRequest, 
    QueryResponse, 
    QueryResult,
    Source
)
from app.services.query_service import QueryService, get_query_service
from app.services.memory_service import MemoryService, get_memory_service
from app.api.deps import get_current_user
from app.models.user import User
from app.core.settings import get_settings

settings = get_settings()
router = APIRouter(prefix="/queries", tags=["Queries"])


@router.post("/", response_model=QueryResponse)
async def process_query(
    request: QueryRequest,
    current_user: User = Depends(get_current_user),
    query_service: QueryService = Depends(get_query_service),
    memory_service: MemoryService = Depends(get_memory_service)
):
    """
    Process a query and return the response with sources.
    
    Uses RAG to find relevant documents and generate a response.
    """
    start_time = time.time()
    
    # Generate query ID
    query_id = str(uuid.uuid4())
    
    # Ensure session exists
    session_id = request.session_id
    if not session_id:
        # Create a new session if not provided
        session_id = await memory_service.create_session(current_user.id)
        
    # Retrieve context from memory if available
    context = []
    if request.use_context:
        context = await memory_service.get_session_context(session_id)
    
    try:
        # Process the query
        result = await query_service.process_query(
            query=request.query,
            user_id=current_user.id,
            session_id=session_id,
            language=request.language or settings.multilingual.default_language,
            max_results=request.max_results or 5,
            include_sources=request.include_sources,
            context=context
        )
        
        # Add to memory if successful
        if result and request.save_to_memory:
            await memory_service.add_to_session(
                session_id=session_id,
                type="query",
                content=request.query,
                metadata={"query_id": query_id}
            )
            
            await memory_service.add_to_session(
                session_id=session_id,
                type="response",
                content=result.answer,
                metadata={
                    "query_id": query_id,
                    "sources": [s.id for s in result.sources]
                }
            )
        
        processing_time = time.time() - start_time
        
        return QueryResponse(
            query_id=query_id,
            session_id=session_id,
            query=request.query,
            result=result,
            processing_time=processing_time,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        # Log error
        import logging
        logging.error(f"Error processing query: {str(e)}", exc_info=True)
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process query: {str(e)}"
        )


@router.get("/history", response_model=List[QueryResponse])
async def get_query_history(
    session_id: Optional[str] = None,
    limit: int = Query(10, ge=1, le=100),
    skip: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    query_service: QueryService = Depends(get_query_service)
):
    """Get query history for the current user."""
    history = await query_service.get_query_history(
        user_id=current_user.id,
        session_id=session_id,
        limit=limit,
        skip=skip
    )
    
    return history


@router.get("/{query_id}", response_model=QueryResponse)
async def get_query(
    query_id: str,
    current_user: User = Depends(get_current_user),
    query_service: QueryService = Depends(get_query_service)
):
    """Get a specific query by ID."""
    query = await query_service.get_query(query_id)
    
    if not query:
        raise HTTPException(status_code=404, detail=f"Query {query_id} not found")
    
    # Check ownership
    if query.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this query")
    
    return query


@router.post("/feedback", response_model=Dict[str, Any])
async def provide_feedback(
    query_id: str = Body(...),
    feedback: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user),
    query_service: QueryService = Depends(get_query_service)
):
    """
    Provide feedback for a query result.
    
    Feedback can include:
    - rating: 1-5 stars
    - thumbs_up: boolean
    - thumbs_down: boolean
    - comments: string
    """
    # Ensure the query exists and belongs to the user
    query = await query_service.get_query(query_id)
    
    if not query:
        raise HTTPException(status_code=404, detail=f"Query {query_id} not found")
    
    if query.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to provide feedback for this query")
    
    # Save feedback
    await query_service.save_feedback(
        query_id=query_id,
        user_id=current_user.id,
        feedback=feedback
    )
    
    return {
        "status": "success",
        "message": "Feedback saved successfully",
        "query_id": query_id
    }


@router.post("/similar-questions", response_model=List[str])
async def generate_similar_questions(
    query: str = Body(...),
    count: int = Body(3, ge=1, le=10),
    current_user: User = Depends(get_current_user),
    query_service: QueryService = Depends(get_query_service)
):
    """
    Generate similar questions to the provided query.
    
    This can be used for query suggestions.
    """
    similar_questions = await query_service.generate_similar_questions(
        query=query,
        user_id=current_user.id,
        count=count
    )
    
    return similar_questions