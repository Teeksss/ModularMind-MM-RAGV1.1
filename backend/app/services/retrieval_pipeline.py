from typing import Dict, Any, List, Optional, Union
import logging
import time
import asyncio

from app.core.settings import get_settings
from app.services.retrievers.base import SearchResult
from app.services.retrievers.hybrid_retriever import HybridRetriever
from app.services.rerankers.cross_encoder_reranker import CrossEncoderReranker
from app.agents.query_expander import QueryExpanderAgent
from app.agents.orchestrator import get_orchestrator

settings = get_settings()
logger = logging.getLogger(__name__)


class RetrievalPipeline:
    """
    Multi-stage retrieval pipeline for improved document retrieval.
    
    Combines:
    1. Query expansion/rewriting
    2. First-stage retrieval (hybrid dense+sparse)
    3. Reranking with cross-encoder
    4. Final retrieval/filtering
    
    This sequential approach improves retrieval quality by applying
    multiple strategies at different stages.
    """
    
    def __init__(
        self,
        use_query_expansion: bool = True,
        use_reranking: bool = True,
        hybrid_retriever_alpha: float = 0.7,
        first_stage_k: int = 30,  # Retrieve more docs in first stage
        final_k: int = 5,  # Return fewer, higher quality docs
        cache_results: bool = True,
        cache_ttl: int = 3600  # 1 hour
    ):
        """
        Initialize the retrieval pipeline.
        
        Args:
            use_query_expansion: Whether to use query expansion
            use_reranking: Whether to use reranking
            hybrid_retriever_alpha: Weight for dense retrieval in hybrid retriever
            first_stage_k: Number of results from first stage retrieval
            final_k: Number of final results
            cache_results: Whether to cache results
            cache_ttl: Cache TTL in seconds
        """
        self.use_query_expansion = use_query_expansion
        self.use_reranking = use_reranking
        self.hybrid_retriever_alpha = hybrid_retriever_alpha
        self.first_stage_k = first_stage_k
        self.final_k = final_k
        self.cache_results = cache_results
        self.cache_ttl = cache_ttl
        
        # Initialize components
        self.hybrid_retriever = HybridRetriever(alpha=hybrid_retriever_alpha)
        self.reranker = CrossEncoderReranker() if use_reranking else None
        self.orchestrator = get_orchestrator() if use_query_expansion else None
        
        # Cache for query results
        self.query_cache = {}  # {query_hash: (timestamp, results)}
        
        logger.info(
            f"Initialized RetrievalPipeline with use_query_expansion={use_query_expansion}, "
            f"use_reranking={use_reranking}, first_stage_k={first_stage_k}, final_k={final_k}"
        )
    
    async def initialize(self) -> None:
        """Initialize the retrieval pipeline."""
        # Initialize hybrid retriever
        await self.hybrid_retriever.initialize()
        
        # Initialize reranker if enabled
        if self.use_reranking and self.reranker:
            await self.reranker.initialize()
    
    async def retrieve(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        k: Optional[int] = None,
        language: str = "en",
        use_metadata: bool = True,
        **kwargs
    ) -> List[SearchResult]:
        """
        Retrieve documents using the multi-stage pipeline.
        
        Args:
            query: The search query
            filters: Optional filters to apply
            k: Number of results to return (overrides final_k)
            language: Query language
            use_metadata: Whether to use metadata in retrieval
            **kwargs: Additional arguments
            
        Returns:
            List of search results
        """
        start_time = time.time()
        
        # Use provided k or default final_k
        final_k = k if k is not None else self.final_k
        
        # Check cache first
        if self.cache_results:
            cache_key = self._get_cache_key(query, final_k, filters, language)
            cached_results = self._get_from_cache(cache_key)
            if cached_results:
                logger.debug(f"Using cached results for query: {query}")
                return cached_results
        
        # Step 1: Query expansion if enabled
        expanded_query = query
        expanded_queries = []
        
        if self.use_query_expansion and self.orchestrator:
            try:
                expander_agent = self.orchestrator.get_agent_instance("QueryExpanderAgent")
                if expander_agent:
                    # Execute query expansion
                    expansion_result = await self.orchestrator.execute_agent(
                        agent_name="QueryExpanderAgent",
                        input_data={"query": query, "language": language}
                    )
                    
                    if expansion_result.success:
                        expanded_query = expansion_result.data.get("rewritten_query", query)
                        expanded_queries = expansion_result.data.get("expanded_queries", [])
                        query_type = expansion_result.data.get("query_type", "unknown")
                        
                        logger.info(
                            f"Query expanded from '{query}' to '{expanded_query}'. "
                            f"Query type: {query_type}"
                        )
                    else:
                        logger.warning(f"Query expansion failed: {expansion_result.error}")
                        
            except Exception as e:
                logger.error(f"Error during query expansion: {str(e)}")
        
        # Step 2: First-stage retrieval
        retrieval_results = []
        
        try:
            # Use the rewritten query for retrieval
            retrieval_results = await self.hybrid_retriever.search(
                query=expanded_query,
                k=self.first_stage_k,
                filters=filters,
                **kwargs
            )
            
            # If we have expanded queries, also retrieve with those and merge results
            if expanded_queries and expanded_query != query:
                # Only use the first expanded query for additional retrieval
                if len(expanded_queries) > 0 and expanded_queries[0] != expanded_query:
                    additional_results = await self.hybrid_retriever.search(
                        query=expanded_queries[0],
                        k=self.first_stage_k // 2,  # Fetch fewer results for expanded query
                        filters=filters,
                        **kwargs
                    )
                    
                    # Add additional results if not already in results
                    existing_ids = {r.id for r in retrieval_results}
                    for result in additional_results:
                        if result.id not in existing_ids:
                            retrieval_results.append(result)
                            existing_ids.add(result.id)
            
            logger.info(f"First-stage retrieval found {len(retrieval_results)} results")
            
        except Exception as e:
            logger.error(f"Error during first-stage retrieval: {str(e)}")
            return []
        
        # Step 3: Reranking if enabled
        if self.use_reranking and self.reranker and len(retrieval_results) > 1:
            try:
                retrieval_results = await self.reranker.rerank(
                    query=query,  # Use original query for reranking
                    results=retrieval_results,
                    top_k=final_k * 2  # Keep twice as many as needed for final filtering
                )
                
                logger.info(f"Reranking completed, top score: {retrieval_results[0].score:.4f}")
                
            except Exception as e:
                logger.error(f"Error during reranking: {str(e)}")
                # Continue with original results if reranking fails
        
        # Step 4: Final filtering and limiting
        # Sort by score and apply final limit
        retrieval_results.sort(key=lambda x: x.score, reverse=True)
        final_results = retrieval_results[:final_k]
        
        # Add metadata about the retrieval process
        for result in final_results:
            result.metadata.update({
                "retrieval_pipeline": "multi_stage",
                "original_query": query,
                "expanded_query": expanded_query if expanded_query != query else None,
                "processing_time": time.time() - start_time
            })
        
        # Cache results
        if self.cache_results:
            cache_key = self._get_cache_key(query, final_k, filters, language)
            self._add_to_cache(cache_key, final_results)
        
        processing_time = time.time() - start_time
        logger.info(
            f"Multi-stage retrieval completed in {processing_time:.3f}s with {len(final_results)} results"
        )
        
        return final_results
    
    def _get_cache_key(
        self,
        query: str,
        k: int,
        filters: Optional[Dict[str, Any]],
        language: str
    ) -> str:
        """Create a cache key for a query."""
        import hashlib
        import json
        
        # Normalize query
        normalized_query = query.lower().strip()
        
        # Create a string representation of filters
        filters_str = ""
        if filters:
            filters_str = json.dumps(filters, sort_keys=True)
        
        # Create a hash of the key components
        key_str = f"{normalized_query}|{k}|{filters_str}|{language}"
        key_hash = hashlib.md5(key_str.encode()).hexdigest()
        
        return key_hash
    
    def _get_from_cache(self, cache_key: str) -> Optional[List[SearchResult]]:
        """Get results from cache if available and not expired."""
        if not self.cache_results:
            return None
        
        cached_data = self.query_cache.get(cache_key)
        if not cached_data:
            return None
        
        timestamp, results = cached_data
        
        # Check if expired
        if time.time() - timestamp > self.cache_ttl:
            # Remove from cache
            del self.query_cache[cache_key]
            return None
        
        return results
    
    def _add_to_cache(self, cache_key: str, results: List[SearchResult]) -> None:
        """Add results to cache."""
        if not self.cache_results:
            return
        
        self.query_cache[cache_key] = (time.time(), results)
        
        # Clean up old cache entries
        self._cleanup_cache()
    
    def _cleanup_cache(self) -> None:
        """Remove expired cache entries."""
        current_time = time.time()
        expired_keys = [
            key for key, (timestamp, _) in self.query_cache.items()
            if current_time - timestamp > self.cache_ttl
        ]
        
        for key in expired_keys:
            del self.query_cache[key]