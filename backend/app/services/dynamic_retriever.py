from typing import Dict, Any, List, Optional, Union
import logging
import time
import re

from app.core.settings import get_settings
from app.services.retrievers.base import BaseRetriever, SearchResult
from app.services.retrievers.hybrid_retriever import HybridRetriever
from app.services.vector_store import get_vector_store
from app.services.retrievers.bm25_retriever import BM25Retriever
from app.agents.query_expander import QueryExpanderAgent
from app.agents.orchestrator import get_orchestrator

settings = get_settings()
logger = logging.getLogger(__name__)


class DynamicRetrieverSelector:
    """
    Dynamic retriever selector that chooses the optimal retrieval strategy.
    
    Analyzes query characteristics to select the most appropriate retrieval method:
    - Pure vector search for semantic/conceptual queries
    - BM25 for keyword queries
    - Hybrid for mixed or complex queries
    """
    
    def __init__(self):
        """Initialize the dynamic retriever selector."""
        # Initialize retrievers
        self.vector_retriever = get_vector_store()
        self.bm25_retriever = BM25Retriever()
        self.hybrid_retriever = HybridRetriever()
        
        # Orchestrator for query analysis
        self.orchestrator = get_orchestrator()
        
        # Query type patterns
        self.keyword_patterns = [
            r'^[a-zA-Z0-9\s]+$',  # Only alphanumeric and spaces
            r'^[\w\s]+[\+\-][\w\s]+$',  # Words with + or - operators
            r'^\w+(\s+\w+){0,3}$'  # 1-4 words only
        ]
        
        self.semantic_patterns = [
            r'\?$',  # Ends with question mark
            r'^(what|who|where|when|why|how|is|are|can|could|would|should)',  # Starts with question word
            r'^(tell|explain|describe|compare|analyze)'  # Starts with instruction verb
        ]
        
        logger.info("Initialized DynamicRetrieverSelector")
    
    async def initialize(self) -> None:
        """Initialize all retrievers."""
        await self.vector_retriever.initialize()
        await self.bm25_retriever.initialize()
        await self.hybrid_retriever.initialize()
    
    async def retrieve(
        self,
        query: str,
        k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        force_method: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Retrieve results using the dynamically selected retrieval method.
        
        Args:
            query: The search query
            k: Number of results to return
            filters: Optional filters to apply
            force_method: Force a specific retrieval method ('vector', 'bm25', 'hybrid')
            **kwargs: Additional arguments
            
        Returns:
            Dict with results and metadata about the retrieval process
        """
        start_time = time.time()
        
        # Analyze query to determine retrieval method
        if force_method:
            retrieval_method = force_method
            analysis_result = {"query_type": "forced", "reasoning": f"Method forced to: {force_method}"}
        else:
            retrieval_method, analysis_result = await self._analyze_query(query)
        
        # Use the selected retriever
        results = []
        
        if retrieval_method == "vector":
            results = await self.vector_retriever.similarity_search(
                query=query,
                k=k,
                filters=filters,
                **kwargs
            )
        elif retrieval_method == "bm25":
            results = await self.bm25_retriever.search(
                query=query,
                k=k,
                filters=filters,
                **kwargs
            )
        else:  # hybrid (default fallback)
            results = await self.hybrid_retriever.search(
                query=query,
                k=k,
                filters=filters,
                **kwargs
            )
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Prepare return data
        return_data = {
            "results": results,
            "metadata": {
                "retrieval_method": retrieval_method,
                "query_type": analysis_result.get("query_type", "unknown"),
                "query_analysis": analysis_result.get("reasoning", ""),
                "processing_time": processing_time,
                "result_count": len(results)
            }
        }
        
        logger.info(
            f"Dynamic retrieval completed in {processing_time:.3f}s using method '{retrieval_method}' "
            f"for query type '{analysis_result.get('query_type', 'unknown')}': {len(results)} results"
        )
        
        return return_data
    
    async def _analyze_query(self, query: str) -> tuple:
        """
        Analyze query to determine the best retrieval method.
        
        Returns:
            Tuple of (retrieval_method, analysis_result)
        """
        # Try using QueryExpanderAgent for analysis if available
        if self.orchestrator:
            try:
                query_analyzer = self.orchestrator.get_agent_instance("QueryExpanderAgent")
                if query_analyzer:
                    # Execute query analysis
                    analysis_result = await self.orchestrator.execute_agent(
                        agent_name="QueryExpanderAgent",
                        input_data={"query": query, "language": "en"}
                    )
                    
                    if analysis_result.success:
                        query_type = analysis_result.data.get("query_type", "unknown")
                        reasoning = analysis_result.data.get("reasoning", "")
                        
                        # Map query type to retrieval method
                        if query_type == "keyword":
                            return "bm25", {"query_type": query_type, "reasoning": reasoning}
                        elif query_type == "natural_language":
                            return "vector", {"query_type": query_type, "reasoning": reasoning}
                        else:  # hybrid or unknown
                            return "hybrid", {"query_type": query_type, "reasoning": reasoning}
            except Exception as e:
                logger.warning(f"Error using QueryExpanderAgent for analysis: {str(e)}")
        
        # Fallback to pattern-based analysis
        return self._pattern_based_analysis(query)
    
    def _pattern_based_analysis(self, query: str) -> tuple:
        """
        Use regex patterns to analyze query type.
        
        Returns:
            Tuple of (retrieval_method, analysis_result)
        """
        # Check for keyword query patterns
        is_keyword = any(re.match(pattern, query) for pattern in self.keyword_patterns)
        
        # Check for semantic query patterns
        is_semantic = any(re.search(pattern, query) for pattern in self.semantic_patterns)
        
        # Determine query type
        if is_keyword and not is_semantic:
            query_type = "keyword"
            method = "bm25"
            reasoning = "Query matches keyword patterns"
        elif is_semantic and not is_keyword:
            query_type = "semantic"
            method = "vector"
            reasoning = "Query matches semantic/natural language patterns"
        else:
            # Mixed or complex query
            query_type = "hybrid"
            method = "hybrid"
            
            if is_keyword and is_semantic:
                reasoning = "Query has both keyword and semantic characteristics"
            else:
                reasoning = "Query has no clear pattern, using hybrid approach"
        
        # Return retrieval method and analysis result
        return method, {"query_type": query_type, "reasoning": reasoning}