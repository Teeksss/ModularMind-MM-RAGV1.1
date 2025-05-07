from typing import Dict, Any, List, Optional, Tuple, Union
import logging
import time
import os
import json
import numpy as np

from app.core.settings import get_settings
from app.services.retrievers.base import SearchResult

settings = get_settings()
logger = logging.getLogger(__name__)

# Optional: Import cross-encoder if available
try:
    from sentence_transformers import CrossEncoder
    DEPENDENCIES_AVAILABLE = True
except ImportError:
    logger.warning("Cross-encoder dependencies not available. Install with: pip install sentence-transformers")
    DEPENDENCIES_AVAILABLE = False


class CrossEncoderReranker:
    """
    Cross-Encoder reranker for improving retrieval results.
    
    Uses a cross-encoder model to rerank search results based on relevance
    to the query, potentially improving retrieval quality over first-stage 
    retriever results.
    """
    
    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        use_gpu: bool = True,
        batch_size: int = 32,
        cache_dir: Optional[str] = None
    ):
        """
        Initialize the cross-encoder reranker.
        
        Args:
            model_name: Name of the cross-encoder model to use
            use_gpu: Whether to use GPU for inference
            batch_size: Batch size for inference
            cache_dir: Directory to cache models
        """
        self.model_name = model_name
        self.use_gpu = use_gpu
        self.batch_size = batch_size
        self.cache_dir = cache_dir
        self.model = None
        
        logger.info(
            f"Initializing CrossEncoderReranker with model={self.model_name}, "
            f"use_gpu={self.use_gpu}, batch_size={self.batch_size}"
        )
    
    async def initialize(self) -> None:
        """Initialize the reranker by loading the model."""
        if not DEPENDENCIES_AVAILABLE:
            logger.error("Cannot initialize CrossEncoderReranker: dependencies not available")
            return
        
        try:
            # Determine device
            device = "cuda" if self.use_gpu else "cpu"
            
            # Load the model
            logger.info(f"Loading cross-encoder model: {self.model_name}")
            self.model = CrossEncoder(self.model_name, device=device, cache_folder=self.cache_dir)
            
            logger.info("Cross-encoder model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading cross-encoder model: {str(e)}")
            self.model = None
    
    async def rerank(
        self,
        query: str,
        results: List[SearchResult],
        top_k: Optional[int] = None,
        threshold: Optional[float] = None
    ) -> List[SearchResult]:
        """
        Rerank results using the cross-encoder model.
        
        Args:
            query: The original search query
            results: List of search results to rerank
            top_k: Number of results to keep after reranking
            threshold: Minimum score threshold for results
            
        Returns:
            Reranked search results
        """
        start_time = time.time()
        
        # Check if model is loaded
        if not self.model:
            logger.warning("Cross-encoder model not loaded, skipping reranking")
            return results
        
        # No need to rerank if only one or zero results
        if len(results) <= 1:
            return results
        
        # Prepare input pairs
        input_pairs = [(query, result.text) for result in results]
        
        # Compute scores
        try:
            cross_encoder_scores = self.model.predict(
                input_pairs,
                batch_size=self.batch_size,
                show_progress_bar=False
            )
        except Exception as e:
            logger.error(f"Error during cross-encoder scoring: {str(e)}")
            return results
        
        # Create updated results with new scores
        reranked_results = []
        for i, (result, score) in enumerate(zip(results, cross_encoder_scores)):
            # Create a new result with updated score
            reranked_result = SearchResult(
                id=result.id,
                text=result.text,
                score=float(score),
                metadata={
                    **result.metadata,
                    "original_score": result.score,
                    "reranker": "cross-encoder",
                    "reranker_model": self.model_name
                }
            )
            reranked_results.append(reranked_result)
        
        # Sort by new scores
        reranked_results.sort(key=lambda x: x.score, reverse=True)
        
        # Apply threshold if provided
        if threshold is not None:
            reranked_results = [r for r in reranked_results if r.score >= threshold]
        
        # Limit to top_k if provided
        if top_k is not None:
            reranked_results = reranked_results[:top_k]
        
        processing_time = time.time() - start_time
        logger.info(
            f"Reranking completed in {processing_time:.3f}s. "
            f"Original results: {len(results)}, Reranked results: {len(reranked_results)}"
        )
        
        return reranked_results