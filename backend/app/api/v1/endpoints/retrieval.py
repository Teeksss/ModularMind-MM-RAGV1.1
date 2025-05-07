from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.models.user import User
from app.services.retrieval_pipeline import RetrievalPipeline
from app.services.dynamic_retriever import DynamicRetrieverSelector
from app.services.context_optimizer import ContextOptimizer, ContextWindow
from app.services.rerankers.cross_encoder_reranker import CrossEncoderReranker
from app.services.retrievers.base import SearchResult
from app.services.retrievers.metadata_retriever import MetadataQuery
from app.services.metrics.retrieval_metrics import get_retrieval_metrics

# Initialize the metrics tracker
retrieval_metrics = get_retrieval_metrics()

router = APIRouter()

# Initialize components
retrieval_pipeline = RetrievalPipeline()
dynamic_retriever = DynamicRetrieverSelector()
context_optimizer = ContextOptimizer()
reranker = CrossEncoderReranker()


class RetrievalRequest(BaseModel):
    """Request model for retrieval endpoint."""
    query: str
    k: int = 5
    method: Optional[str] = None  # "pipeline", "dynamic", "hybrid", "vector", "bm25"
    filters: Optional[Dict[str, Any]] = None
    rerank: Optional[bool] = None
    optimize_context: Optional[bool] = None
    metadata_query: Optional[MetadataQuery] = None
    explain: bool = False


class RetrievalResponse(BaseModel):
    """Response model for retrieval endpoint."""
    results: List[Dict[str, Any]]
    context: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


@router.post(
    "/search",
    response_model=RetrievalResponse,
    summary="Perform an advanced search using the retrieval system"
)
@retrieval_metrics.track_retrieval(method="api")
async def search(
    request: RetrievalRequest,
    current_user: User = Depends(get_current_user),
    track_stage: Optional[Any] = None
) -> RetrievalResponse:
    """
    Perform an advanced search using various retrieval methods.
    
    - Use different retrieval strategies based on query characteristics
    - Apply reranking for improved relevance
    - Optimize context window for more effective LLM consumption
    """
    if track_stage:
        track_stage("initialize", start=True)
    
    # Initialize components if needed
    if not hasattr(retrieval_pipeline, "_initialized"):
        await retrieval_pipeline.initialize()
        await dynamic_retriever.initialize()
        await reranker.initialize()
        retrieval_pipeline._initialized = True
    
    if track_stage:
        track_stage("initialize", start=False)
        track_stage("retrieve", start=True)
    
    try:
        # Record metrics about query type if available
        if request.method:
            retrieval_metrics.record_query_type(request.method)
        
        # Decide which retrieval method to use
        method = request.method or "pipeline"
        results = []
        metadata = {}
        
        # Retrieve results based on method
        if method == "pipeline":
            # Use multi-stage retrieval pipeline
            results = await retrieval_pipeline.retrieve(
                query=request.query,
                filters=request.filters,
                k=request.k,
                language="en"  # Could be made dynamic
            )
            metadata["method"] = "multi_stage_pipeline"
            
        elif method == "dynamic":
            # Use dynamic retriever selection
            retrieval_result = await dynamic_retriever.retrieve(
                query=request.query,
                k=request.k,
                filters=request.filters
            )
            results = retrieval_result["results"]
            metadata = retrieval_result["metadata"]
            
        else:
            # Use specified method directly
            if method == "hybrid":
                from app.services.retrievers.hybrid_retriever import HybridRetriever
                retriever = HybridRetriever()
            elif method == "vector":
                from app.services.vector_store import get_vector_store
                retriever = get_vector_store()
            elif method == "bm25":
                from app.services.retrievers.bm25_retriever import BM25Retriever
                retriever = BM25Retriever()
            else:
                raise HTTPException(status_code=400, detail=f"Invalid retrieval method: {method}")
            
            # Initialize retriever if needed
            await retriever.initialize()
            
            # Retrieve results
            results = await retriever.search(
                query=request.query,
                k=request.k,
                filters=request.filters
            )
            metadata["method"] = method
        
        if track_stage:
            track_stage("retrieve", start=False)
            track_stage("post_process", start=True)
        
        # Apply reranking if requested
        if request.rerank or (request.rerank is None and request.method != "pipeline"):
            original_results = results
            results = await reranker.rerank(
                query=request.query,
                results=results,
                top_k=request.k
            )
            metadata["reranked"] = True
            metadata["original_results_count"] = len(original_results)
        
        # Optimize context if requested
        context = None
        if request.optimize_context or (request.optimize_context is None and len(results) > 1):
            context_window = await context_optimizer.optimize(
                results=results,
                query=request.query,
                strategy="coverage"
            )
            context = {
                "text": "\n\n".join([chunk.text for chunk in context_window.chunks]),
                "total_tokens": context_window.total_tokens,
                "total_chars": context_window.total_chars,
                "chunk_count": len(context_window.chunks),
                "sources": list(context_window.sources.values())
            }
        
        # Record metrics about result count
        retrieval_metrics.record_results(method, len(results))
        
        # Prepare the response
        response_results = []
        for result in results:
            response_results.append({
                "id": result.id,
                "text": result.text,
                "score": result.score,
                "metadata": result.metadata
            })
        
        if track_stage:
            track_stage("post_process", start=False)
        
        # Add more metadata for explain mode
        if request.explain:
            metadata["detailed_metrics"] = retrieval_metrics.get_metrics()
        
        return RetrievalResponse(
            results=response_results,
            context=context,
            metadata=metadata
        )
        
    except Exception as e:
        if track_stage:
            track_stage("error", start=True)
            track_stage("error", start=False)
        raise HTTPException(status_code=500, detail=f"Retrieval error: {str(e)}")


@router.get(
    "/metrics",
    response_model=Dict[str, Any],
    summary="Get retrieval system metrics"
)
async def get_metrics(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get performance metrics for the retrieval system."""
    # Check if user has admin permissions
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get metrics
    metrics = retrieval_metrics.get_metrics()
    
    return metrics