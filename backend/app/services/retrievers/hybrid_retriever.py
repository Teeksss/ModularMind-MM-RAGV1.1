from typing import Dict, Any, List, Optional, Tuple, Union
import logging
import time
import numpy as np
from pydantic import BaseModel, Field

from app.core.settings import get_settings
from app.services.vector_store import get_vector_store
from app.services.retrievers.bm25_retriever import BM25Retriever
from app.services.retrievers.base import BaseRetriever, SearchResult

settings = get_settings()
logger = logging.getLogger(__name__)


class HybridSearchResult(BaseModel):
    """Result from hybrid search including combined score."""
    id: str
    text: str
    score: float  # Dense retrieval score
    bm25_score: float  # Sparse retrieval score
    combined_score: float  # Combined score
    metadata: Dict[str, Any] = Field(default_factory=dict)


class HybridRetriever(BaseRetriever):
    """
    Hybrid retriever that combines dense and sparse retrieval.
    
    Performs both vector similarity search and BM25 keyword search,
    then combines the results with a configurable weighting.
    """
    
    def __init__(
        self,
        alpha: float = 0.7,  # Weight for dense retrieval (1-alpha for sparse)
        normalize_scores: bool = True,
        use_reciprocal_rank_fusion: bool = False
    ):
        """
        Initialize the hybrid retriever.
        
        Args:
            alpha: Weight for dense retrieval (0.0 to 1.0)
            normalize_scores: Whether to normalize scores before combining
            use_reciprocal_rank_fusion: Use RRF instead of weighted average
        """
        self.vector_store = get_vector_store()
        self.bm25_retriever = BM25Retriever()
        self.alpha = max(0.0, min(1.0, alpha))  # Ensure alpha is between 0 and 1
        self.normalize_scores = normalize_scores
        self.use_reciprocal_rank_fusion = use_reciprocal_rank_fusion
        super().__init__()
        
        logger.info(
            f"Initialized HybridRetriever with alpha={self.alpha}, "
            f"normalize_scores={self.normalize_scores}, "
            f"use_reciprocal_rank_fusion={self.use_reciprocal_rank_fusion}"
        )
    
    async def initialize(self) -> None:
        """Initialize the hybrid retriever."""
        # Ensure vector store is initialized
        await self.vector_store.initialize()
        
        # Initialize BM25 retriever
        await self.bm25_retriever.initialize()
    
    async def search(
        self,
        query: str,
        k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        alpha: Optional[float] = None,
        **kwargs
    ) -> List[SearchResult]:
        """
        Perform hybrid search using both dense and sparse retrieval.
        
        Args:
            query: The search query
            k: Number of results to return
            filters: Optional filters to apply to the search
            alpha: Override the default alpha value
            **kwargs: Additional arguments to pass to the retrievers
            
        Returns:
            List of search results with combined scores
        """
        start_time = time.time()
        
        # Use provided alpha if given, otherwise use default
        search_alpha = alpha if alpha is not None else self.alpha
        
        # Retrieve more results than needed for better merging
        retrieve_k = max(k * 2, 20)
        
        # Start both searches concurrently
        dense_results_future = self.vector_store.similarity_search(
            query=query,
            k=retrieve_k,
            filters=filters,
            **kwargs
        )
        
        sparse_results_future = self.bm25_retriever.search(
            query=query,
            k=retrieve_k,
            filters=filters,
            **kwargs
        )
        
        # Wait for both to complete
        dense_results = await dense_results_future
        sparse_results = await sparse_results_future
        
        # Convert to dictionaries for efficient lookups
        dense_dict = {result.id: result for result in dense_results}
        sparse_dict = {result.id: result for result in sparse_results}
        
        # Get all unique document IDs
        all_ids = set(dense_dict.keys()) | set(sparse_dict.keys())
        
        # Combine results
        hybrid_results = []
        
        for doc_id in all_ids:
            dense_result = dense_dict.get(doc_id)
            sparse_result = sparse_dict.get(doc_id)
            
            # Skip if missing from either set when using RRF
            if self.use_reciprocal_rank_fusion and (not dense_result or not sparse_result):
                continue
            
            # Get scores, defaulting to 0 if not in one of the result sets
            dense_score = dense_result.score if dense_result else 0.0
            sparse_score = sparse_result.score if sparse_result else 0.0
            
            # Get text and metadata from whichever result is available
            text = (dense_result or sparse_result).text
            metadata = (dense_result or sparse_result).metadata
            
            # Create hybrid result with combined score
            hybrid_results.append(HybridSearchResult(
                id=doc_id,
                text=text,
                score=dense_score,
                bm25_score=sparse_score,
                combined_score=0.0,  # Will be calculated below
                metadata=metadata
            ))
        
        # Calculate combined scores based on strategy
        if self.use_reciprocal_rank_fusion:
            hybrid_results = self._combine_with_rrf(hybrid_results, dense_results, sparse_results)
        else:
            hybrid_results = self._combine_with_weights(hybrid_results, search_alpha)
        
        # Sort by combined score and limit to k results
        hybrid_results.sort(key=lambda x: x.combined_score, reverse=True)
        hybrid_results = hybrid_results[:k]
        
        # Calculate processing time
        processing_time = time.time() - start_time
        logger.info(f"Hybrid search completed in {processing_time:.3f}s with {len(hybrid_results)} results")
        
        # Convert to standard SearchResult
        final_results = [
            SearchResult(
                id=result.id,
                text=result.text,
                score=result.combined_score,
                metadata={
                    **result.metadata,
                    "dense_score": result.score,
                    "sparse_score": result.bm25_score,
                    "combined_score": result.combined_score,
                    "retrieval_method": "hybrid"
                }
            )
            for result in hybrid_results
        ]
        
        return final_results
    
    def _combine_with_weights(
        self,
        hybrid_results: List[HybridSearchResult],
        alpha: float
    ) -> List[HybridSearchResult]:
        """Combine scores using weighted average."""
        if not hybrid_results:
            return []
        
        # Normalize scores if enabled
        if self.normalize_scores:
            # Get all scores for normalization
            dense_scores = [r.score for r in hybrid_results if r.score > 0]
            sparse_scores = [r.bm25_score for r in hybrid_results if r.bm25_score > 0]
            
            # Calculate normalization factors (avoid division by zero)
            dense_max = max(dense_scores) if dense_scores else 1.0
            sparse_max = max(sparse_scores) if sparse_scores else 1.0
            
            # Normalize scores
            for result in hybrid_results:
                result.score = result.score / dense_max if dense_max > 0 else 0
                result.bm25_score = result.bm25_score / sparse_max if sparse_max > 0 else 0
        
        # Combine scores with weighted average
        for result in hybrid_results:
            result.combined_score = (alpha * result.score) + ((1 - alpha) * result.bm25_score)
        
        return hybrid_results
    
    def _combine_with_rrf(
        self,
        hybrid_results: List[HybridSearchResult],
        dense_results: List[SearchResult],
        sparse_results: List[SearchResult]
    ) -> List[HybridSearchResult]:
        """Combine using Reciprocal Rank Fusion."""
        # Constant for RRF calculation
        k = 60  # Standard value from literature
        
        # Get dense and sparse rankings
        dense_ranks = {r.id: i+1 for i, r in enumerate(dense_results)}
        sparse_ranks = {r.id: i+1 for i, r in enumerate(sparse_results)}
        
        # Calculate RRF scores
        for result in hybrid_results:
            dense_rank = dense_ranks.get(result.id, len(dense_results) + 1)
            sparse_rank = sparse_ranks.get(result.id, len(sparse_results) + 1)
            
            # RRF formula: sum of 1/(k + rank) for each retriever
            rrf_dense = 1 / (k + dense_rank)
            rrf_sparse = 1 / (k + sparse_rank)
            result.combined_score = rrf_dense + rrf_sparse
        
        return hybrid_results