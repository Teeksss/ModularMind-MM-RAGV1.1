import logging
from typing import Dict, List, Optional, Any, Union
import time

from app.core.config import settings
from app.services.retrieval_pipeline import RetrievalPipeline
from app.services.context_optimizer import ContextOptimizer
from app.services.attribution_enhancer import AttributionEnhancer
from app.agents.answer_validator import AnswerValidatorAgent
from app.agents.orchestrator import get_orchestrator
from app.services.llm_service import get_llm_service
from app.utils.metrics import get_retrieval_metrics

logger = logging.getLogger(__name__)
retrieval_metrics = get_retrieval_metrics()


class RAGService:
    """
    Comprehensive RAG service that combines:
    - Advanced retrieval
    - Context optimization
    - Structured prompting
    - Source attribution
    - Answer validation
    
    This service coordinates the entire RAG process from query to validated response.
    """
    
    def __init__(self):
        """Initialize the RAG service."""
        self.retrieval_pipeline = RetrievalPipeline()
        self.context_optimizer = ContextOptimizer()
        self.attribution_enhancer = AttributionEnhancer()
        self.orchestrator = get_orchestrator()
        self.llm_service = get_llm_service()
    
    async def initialize(self) -> None:
        """Initialize all components."""
        await self.retrieval_pipeline.initialize()
    
    @retrieval_metrics.track_retrieval(method="rag_service")
    async def process_query(
        self,
        query: str,
        chat_history: Optional[List[Dict[str, Any]]] = None,
        user_id: Optional[str] = None,
        optimize_context: bool = True,
        validate_answer: bool = True,
        retrieval_options: Optional[Dict[str, Any]] = None,
        llm_options: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Process a query through the complete RAG pipeline.
        
        Args:
            query: User query
            chat_history: Optional chat history for context
            user_id: Optional user ID for personalization
            optimize_context: Whether to optimize context window
            validate_answer: Whether to validate the answer
            retrieval_options: Options for the retrieval pipeline
            llm_options: Options for the LLM service
            **kwargs: Additional options
            
        Returns:
            Dict containing response and metadata
        """
        start_time = time.time()
        output = {
            "query": query,
            "processing_times": {},
            "metadata": {}
        }
        
        try:
            # Step 1: Retrieve relevant documents
            retrieval_start = time.time()
            
            retrieval_results = await self.retrieval_pipeline.retrieve(
                query=query,
                **(retrieval_options or {})
            )
            
            retrieval_time = time.time() - retrieval_start
            output["processing_times"]["retrieval"] = retrieval_time
            
            # Short circuit if no results found
            if not retrieval_results:
                output["response"] = "I couldn't find any relevant information to answer your question."
                output["sources"] = []
                output["metadata"]["retrieval_count"] = 0
                return output
            
            # Step 2: Optimize context window if enabled
            if optimize_context:
                optimization_start = time.time()
                
                optimized_context = await self.context_optimizer.optimize(
                    results=retrieval_results,
                    query=query,
                    strategy="coverage"  # Choose strategy based on query complexity
                )
                
                # Use optimized context
                context_docs = optimized_context.chunks
                
                optimization_time = time.time() - optimization_start
                output["processing_times"]["context_optimization"] = optimization_time
                output["metadata"]["context_optimization"] = {
                    "strategy": "coverage",
                    "chunks_before": len(retrieval_results),
                    "chunks_after": len(context_docs),
                    "tokens": optimized_context.total_tokens
                }
            else:
                # Use retrieval results directly
                context_docs = retrieval_results
            
            # Step 3: Format context for LLM
            context_text = "\n\n".join([doc.text for doc in context_docs])
            
            # Step 4: Generate response with LLM
            generation_start = time.time()
            
            llm_response = await self.llm_service.generate_rag_response(
                query=query,
                context=context_text,
                chat_history=chat_history,
                **(llm_options or {})
            )
            
            generation_time = time.time() - generation_start
            output["processing_times"]["llm_generation"] = generation_time
            
            # Step 5: Add source attribution
            attribution_start = time.time()
            
            enhanced_response = await self.attribution_enhancer.enhance(
                response=llm_response,
                sources=context_docs,
                query=query
            )
            
            attribution_time = time.time() - attribution_start
            output["processing_times"]["source_attribution"] = attribution_time
            
            # Step 6: Validate answer if enabled
            if validate_answer:
                validation_start = time.time()
                
                validation_result = await self.orchestrator.execute_agent(
                    agent_name="AnswerValidatorAgent",
                    input_data={
                        "question": query,
                        "answer": enhanced_response.response,
                        "sources": [doc.text for doc in context_docs]
                    }
                )
                
                validation_time = time.time() - validation_start
                output["processing_times"]["answer_validation"] = validation_time
                
                if validation_result.success:
                    output["validation"] = validation_result.data
                    
                    # Add warning if factuality is low
                    if validation_result.data["factuality_score"] < 0.7:
                        warning = "Note: This response may contain information not fully supported by the source documents."
                        output["warning"] = warning
            
            # Prepare final output
            output["response"] = enhanced_response.response
            output["sources"] = list(enhanced_response.sources.values())
            output["citations"] = enhanced_response.citations
            output["markdown"] = enhanced_response.markdown
            output["metadata"]["retrieval_count"] = len(retrieval_results)
            
            # Calculate total processing time
            total_time = time.time() - start_time
            output["processing_times"]["total"] = total_time
            
            return output
            
        except Exception as e:
            logger.error(f"Error in RAG process: {str(e)}", exc_info=True)
            output["error"] = str(e)
            output["response"] = "I'm sorry, I encountered an error while processing your query."
            return output


# Singleton instance
_rag_service = None

def get_rag_service() -> RAGService:
    """Get the RAG service singleton."""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service