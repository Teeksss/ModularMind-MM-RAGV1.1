from typing import Dict, List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from app.api.deps import get_current_user, get_optional_user
from app.models.user import User
from app.services.vector_store import get_vector_store
from app.services.retrieval_pipeline import RetrievalPipeline
from app.services.attribution_enhancer import AttributionEnhancer
from app.agents.orchestrator import get_orchestrator
from app.services.llm_service import get_llm_service
from app.services.metrics.retrieval_metrics import get_retrieval_metrics
from app.services.context_optimizer import ContextOptimizer

router = APIRouter()
retrieval_metrics = get_retrieval_metrics()


class QueryRequest(BaseModel):
    """Request model for query endpoint."""
    query: str
    filters: Optional[Dict[str, Any]] = None
    top_k: int = 5
    include_sources: bool = True
    validate_answer: bool = True
    model: Optional[str] = None
    stream: bool = False


class QueryResponse(BaseModel):
    """Response model for query endpoint."""
    query: str
    answer: str
    sources: Optional[List[Dict[str, Any]]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


@router.post(
    "/", 
    response_model=QueryResponse,
    summary="Generate an answer for a query using RAG"
)
@retrieval_metrics.track_retrieval(method="query")
async def query(
    request: QueryRequest,
    background_tasks: BackgroundTasks,
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Generate an answer for a query using Retrieval Augmented Generation (RAG).
    
    The system will:
    1. Retrieve relevant documents using the advanced retrieval system
    2. Optimize the context from retrieved documents
    3. Generate an answer using the LLM
    4. Validate the answer for factual accuracy
    5. Add source attributions to the answer
    
    Returns the answer with source references.
    """
    try:
        # Initialize retrieval pipeline
        retrieval_pipeline = RetrievalPipeline(
            use_query_expansion=True, 
            use_reranking=True
        )
        await retrieval_pipeline.initialize()
        
        # Initialize attribution enhancer
        attribution_enhancer = AttributionEnhancer()
        
        # Initialize LLM service
        llm_service = get_llm_service()
        
        # Initialize orchestrator for agents
        orchestrator = get_orchestrator()
        
        # Initialize context optimizer
        context_optimizer = ContextOptimizer()
        
        # 1. Retrieve relevant documents
        retrieval_results = await retrieval_pipeline.retrieve(
            query=request.query,
            filters=request.filters,
            k=request.top_k
        )
        
        # 2. Optimize context
        optimized_context = await context_optimizer.optimize(
            results=retrieval_results,
            query=request.query,
            strategy="coverage"
        )
        
        # Create context text
        context_text = "\n\n".join([chunk.text for chunk in optimized_context.chunks])
        
        # 3. Generate answer with LLM
        prompt = f"""
        Answer the following question using ONLY the provided context. 
        If the answer cannot be found in the context, say "I don't have enough information to answer this question."
        
        Question: {request.query}
        
        Context:
        {context_text}
        
        Answer:
        """
        
        # Generate answer
        raw_response = await llm_service.generate(
            prompt=prompt,
            model=request.model
        )
        
        # 4. Add source attributions
        enhanced_response = await attribution_enhancer.enhance(
            response=raw_response,
            sources=retrieval_results,
            query=request.query,
            auto_detect=True
        )
        
        # 5. Validate answer if requested
        if request.validate_answer:
            # Run validation in background to avoid blocking
            background_tasks.add_task(
                validate_answer,
                orchestrator, 
                request.query, 
                enhanced_response.response, 
                retrieval_results
            )
        
        # Prepare sources for response
        sources = None
        if request.include_sources:
            sources = [
                {
                    "id": source["id"],
                    "title": source["title"],
                    "url": source.get("url"),
                    "content_type": source.get("content_type", "text")
                }
                for source in enhanced_response.sources.values()
            ]
        
        # Return response
        return QueryResponse(
            query=request.query,
            answer=enhanced_response.response,
            sources=sources,
            metadata={
                "retrieval_method": retrieval_pipeline.method,
                "sources_count": len(enhanced_response.sources),
                "citations_count": len(enhanced_response.citations),
                "context_tokens": optimized_context.total_tokens
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query processing error: {str(e)}")


async def validate_answer(
    orchestrator, 
    question: str, 
    answer: str, 
    sources: List[Any]
):
    """Validate the answer against sources (runs in background)."""
    try:
        validation_result = await orchestrator.execute_agent(
            agent_name="AnswerValidatorAgent",
            input_data={
                "question": question,
                "answer": answer,
                "sources": sources
            }
        )
        
        # Log validation results
        if validation_result.success:
            data = validation_result.data
            logger.info(
                f"Answer validation: factuality={data['factuality_score']:.2f}, "
                f"hallucination={data['hallucination_score']:.2f}, "
                f"valid={data['is_valid']}"
            )
        else:
            logger.warning(f"Answer validation failed: {validation_result.error}")
            
    except Exception as e:
        logger.error(f"Error in answer validation: {str(e)}")