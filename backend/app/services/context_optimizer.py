from typing import Dict, Any, List, Optional, Union
import logging
import time
import re
from pydantic import BaseModel, Field
import heapq

from app.core.settings import get_settings
from app.services.retrievers.base import SearchResult
from app.services.llm_service import get_llm_service

settings = get_settings()
logger = logging.getLogger(__name__)


class DocChunk(BaseModel):
    """Model for a document chunk used in context optimization."""
    id: str
    text: str
    score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)
    order: Optional[int] = None
    source_doc_id: Optional[str] = None


class ContextWindow(BaseModel):
    """Model for an optimized context window."""
    chunks: List[DocChunk] = Field(default_factory=list)
    total_tokens: int
    total_chars: int
    sources: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ContextOptimizer:
    """
    Optimizer for creating optimal context windows from retrieved chunks.
    
    Applies various strategies to select and order chunks to maximize
    information density and relevance within token constraints.
    """
    
    def __init__(
        self,
        max_tokens: int = 3000,
        max_chunks: int = 10,
        overlap_threshold: float = 0.7,
        diversity_weight: float = 0.3,
        preserve_order: bool = False,
        tokenizer: Optional[Any] = None
    ):
        """
        Initialize the context optimizer.
        
        Args:
            max_tokens: Maximum tokens in the context window
            max_chunks: Maximum number of chunks to include
            overlap_threshold: Threshold for detecting duplicate content
            diversity_weight: Weight for diversity vs relevance (0.0 to 1.0)
            preserve_order: Whether to preserve original document order
            tokenizer: Optional custom tokenizer
        """
        self.max_tokens = max_tokens
        self.max_chunks = max_chunks
        self.overlap_threshold = overlap_threshold
        self.diversity_weight = diversity_weight
        self.preserve_order = preserve_order
        self.tokenizer = tokenizer
        self.llm_service = get_llm_service()
        
        logger.info(
            f"Initialized ContextOptimizer with max_tokens={max_tokens}, "
            f"max_chunks={max_chunks}, diversity_weight={diversity_weight}"
        )
    
    async def optimize(
        self,
        results: List[SearchResult],
        query: str,
        strategy: str = "greedy",
        custom_max_tokens: Optional[int] = None
    ) -> ContextWindow:
        """
        Optimize the context window from search results.
        
        Args:
            results: List of search results to optimize
            query: Original query for relevance calculation
            strategy: Optimization strategy ('greedy', 'relevance', 'coverage', or 'diverse')
            custom_max_tokens: Optional override for max_tokens
            
        Returns:
            Optimized context window
        """
        start_time = time.time()
        
        # Use custom max tokens if provided
        max_tokens = custom_max_tokens or self.max_tokens
        
        # Convert results to DocChunks
        chunks = self._convert_results_to_chunks(results)
        
        # Apply the selected optimization strategy
        if strategy == "greedy":
            optimized_chunks = self._apply_greedy_strategy(chunks, query, max_tokens)
        elif strategy == "relevance":
            optimized_chunks = self._apply_relevance_strategy(chunks, max_tokens)
        elif strategy == "coverage":
            optimized_chunks = self._apply_coverage_strategy(chunks, query, max_tokens)
        elif strategy == "diverse":
            optimized_chunks = self._apply_diversity_strategy(chunks, max_tokens)
        else:
            logger.warning(f"Unknown optimization strategy '{strategy}', falling back to greedy")
            optimized_chunks = self._apply_greedy_strategy(chunks, query, max_tokens)
        
        # Create the context window
        context_window = self._create_context_window(optimized_chunks)
        
        processing_time = time.time() - start_time
        logger.info(
            f"Context optimization ({strategy}) completed in {processing_time:.3f}s: "
            f"{len(optimized_chunks)} chunks, {context_window.total_tokens} tokens"
        )
        
        return context_window
    
    def _convert_results_to_chunks(self, results: List[SearchResult]) -> List[DocChunk]:
        """Convert search results to DocChunks."""
        chunks = []
        
        for i, result in enumerate(results):
            # Extract source_doc_id if available
            source_doc_id = result.metadata.get("document_id", None)
            
            # Create DocChunk
            chunk = DocChunk(
                id=result.id,
                text=result.text,
                score=result.score,
                metadata=result.metadata,
                order=i,  # preserve original order
                source_doc_id=source_doc_id
            )
            
            chunks.append(chunk)
        
        return chunks
    
    def _apply_greedy_strategy(
        self,
        chunks: List[DocChunk],
        query: str,
        max_tokens: int
    ) -> List[DocChunk]:
        """
        Apply a greedy optimization strategy.
        
        Selects chunks in order of score until token limit is reached,
        with deduplication to avoid redundant content.
        """
        # Sort by score (highest first)
        sorted_chunks = sorted(chunks, key=lambda x: x.score, reverse=True)
        
        selected_chunks = []
        tokens_used = 0
        selected_doc_ids = set()
        
        for chunk in sorted_chunks:
            # Skip if we've reached max chunks
            if len(selected_chunks) >= self.max_chunks:
                break
            
            # Get token count for this chunk
            chunk_tokens = self._count_tokens(chunk.text)
            
            # Skip if this would exceed token limit
            if tokens_used + chunk_tokens > max_tokens:
                continue
            
            # Check for document ID - avoid too many chunks from same doc
            if chunk.source_doc_id:
                if chunk.source_doc_id in selected_doc_ids and len(selected_doc_ids) >= 3:
                    # Skip if we already have content from 3+ different docs
                    # and this doc is already represented
                    continue
            
            # Check for content overlap
            if self._has_significant_overlap(chunk, selected_chunks):
                continue
            
            # Add chunk
            selected_chunks.append(chunk)
            tokens_used += chunk_tokens
            
            # Track document ID
            if chunk.source_doc_id:
                selected_doc_ids.add(chunk.source_doc_id)
        
        # Restore original order if needed
        if self.preserve_order:
            selected_chunks.sort(key=lambda x: x.order or 0)
        
        return selected_chunks
    
    def _apply_relevance_strategy(
        self,
        chunks: List[DocChunk],
        max_tokens: int
    ) -> List[DocChunk]:
        """
        Apply a pure relevance-based strategy.
        
        Prioritizes relevance score above all else.
        """
        # Sort by score (highest first)
        sorted_chunks = sorted(chunks, key=lambda x: x.score, reverse=True)
        
        selected_chunks = []
        tokens_used = 0
        
        for chunk in sorted_chunks:
            # Skip if we've reached max chunks
            if len(selected_chunks) >= self.max_chunks:
                break
            
            # Get token count for this chunk
            chunk_tokens = self._count_tokens(chunk.text)
            
            # Skip if this would exceed token limit
            if tokens_used + chunk_tokens > max_tokens:
                continue
            
            # Add chunk
            selected_chunks.append(chunk)
            tokens_used += chunk_tokens
        
        # Restore original order if needed
        if self.preserve_order:
            selected_chunks.sort(key=lambda x: x.order or 0)
        
        return selected_chunks
    
    def _apply_coverage_strategy(
        self,
        chunks: List[DocChunk],
        query: str,
        max_tokens: int
    ) -> List[DocChunk]:
        """
        Apply a coverage-based strategy.
        
        Aims to include diverse chunks covering different aspects
        of the query, even if they have lower relevance scores.
        """
        # Start with highest scored chunk
        sorted_chunks = sorted(chunks, key=lambda x: x.score, reverse=True)
        
        if not sorted_chunks:
            return []
        
        selected_chunks = [sorted_chunks[0]]
        tokens_used = self._count_tokens(sorted_chunks[0].text)
        remaining_chunks = sorted_chunks[1:]
        
        # Initialize query coverage terms
        query_terms = self._extract_key_terms(query)
        covered_terms = self._extract_key_terms(sorted_chunks[0].text)
        
        while remaining_chunks and len(selected_chunks) < self.max_chunks:
            best_chunk = None
            best_score = -1
            
            for i, chunk in enumerate(remaining_chunks):
                # Skip if this would exceed token limit
                chunk_tokens = self._count_tokens(chunk.text)
                if tokens_used + chunk_tokens > max_tokens:
                    continue
                
                # Skip if too much overlap
                if self._has_significant_overlap(chunk, selected_chunks):
                    continue
                
                # Calculate coverage improvement
                chunk_terms = self._extract_key_terms(chunk.text)
                new_terms = len(chunk_terms - covered_terms)
                coverage_score = new_terms / max(1, len(chunk_terms))
                
                # Weighted score combining relevance and coverage
                combined_score = (
                    (1 - self.diversity_weight) * chunk.score + 
                    self.diversity_weight * coverage_score
                )
                
                if combined_score > best_score:
                    best_score = combined_score
                    best_chunk = (i, chunk)
            
            if best_chunk is None:
                break
            
            # Add best chunk
            index, chunk = best_chunk
            selected_chunks.append(chunk)
            tokens_used += self._count_tokens(chunk.text)
            
            # Update covered terms
            covered_terms.update(self._extract_key_terms(chunk.text))
            
            # Remove from remaining
            remaining_chunks.pop(index)
        
        # Restore original order if needed
        if self.preserve_order:
            selected_chunks.sort(key=lambda x: x.order or 0)
        
        return selected_chunks
    
    def _apply_diversity_strategy(
        self,
        chunks: List[DocChunk],
        max_tokens: int
    ) -> List[DocChunk]:
        """
        Apply a diversity-based strategy.
        
        Ensures selected chunks come from different documents
        to provide broad coverage of available sources.
        """
        # Group chunks by source document
        doc_chunks = {}
        for chunk in chunks:
            doc_id = chunk.source_doc_id or chunk.id
            if doc_id not in doc_chunks:
                doc_chunks[doc_id] = []
            doc_chunks[doc_id].append(chunk)
        
        # Sort each document's chunks by score
        for doc_id in doc_chunks:
            doc_chunks[doc_id].sort(key=lambda x: x.score, reverse=True)
        
        # Create a priority queue of top chunks from each document
        chunk_queue = []
        for doc_id, doc_chunk_list in doc_chunks.items():
            if doc_chunk_list:
                heapq.heappush(chunk_queue, (-doc_chunk_list[0].score, doc_id, 0))
        
        # Select chunks in round-robin fashion from different docs
        selected_chunks = []
        tokens_used = 0
        
        while chunk_queue and len(selected_chunks) < self.max_chunks:
            # Get highest scored chunk
            neg_score, doc_id, index = heapq.heappop(chunk_queue)
            chunk = doc_chunks[doc_id][index]
            
            # Check token limit
            chunk_tokens = self._count_tokens(chunk.text)
            if tokens_used + chunk_tokens > max_tokens:
                # Try next chunk from this document if available
                if index + 1 < len(doc_chunks[doc_id]):
                    heapq.heappush(chunk_queue, (-doc_chunks[doc_id][index + 1].score, doc_id, index + 1))
                continue
            
            # Check for overlap
            if not self._has_significant_overlap(chunk, selected_chunks):
                selected_chunks.append(chunk)
                tokens_used += chunk_tokens
            
            # Add next chunk from this document to queue if available
            if index + 1 < len(doc_chunks[doc_id]):
                heapq.heappush(chunk_queue, (-doc_chunks[doc_id][index + 1].score, doc_id, index + 1))
        
        # Restore original order if needed
        if self.preserve_order:
            selected_chunks.sort(key=lambda x: x.order or 0)
        
        return selected_chunks
    
    def _create_context_window(self, chunks: List[DocChunk]) -> ContextWindow:
        """Create a context window from selected chunks."""
        total_tokens = sum(self._count_tokens(chunk.text) for chunk in chunks)
        total_chars = sum(len(chunk.text) for chunk in chunks)
        
        # Collect source information
        sources = {}
        for chunk in chunks:
            doc_id = chunk.source_doc_id or chunk.id
            if doc_id not in sources:
                # Get source metadata
                title = chunk.metadata.get("title", "Unknown")
                url = chunk.metadata.get("url", None)
                content_type = chunk.metadata.get("content_type", "text")
                
                sources[doc_id] = {
                    "id": doc_id,
                    "title": title,
                    "url": url,
                    "content_type": content_type,
                    "chunk_count": 1
                }
            else:
                sources[doc_id]["chunk_count"] += 1
        
        # Create context window
        context_window = ContextWindow(
            chunks=chunks,
            total_tokens=total_tokens,
            total_chars=total_chars,
            sources=sources,
            metadata={
                "chunk_count": len(chunks),
                "optimization_strategy": "greedy" if self.preserve_order else "relevance"
            }
        )
        
        return context_window
    
    def _has_significant_overlap(self, chunk: DocChunk, selected_chunks: List[DocChunk]) -> bool:
        """Check if a chunk has significant overlap with already selected chunks."""
        if not selected_chunks:
            return False
        
        # Extract sentences from new chunk
        chunk_sentences = self._split_into_sentences(chunk.text)
        
        for selected in selected_chunks:
            # Extract sentences from selected chunk
            selected_sentences = self._split_into_sentences(selected.text)
            
            # Count overlapping sentences
            overlap_count = 0
            for sentence in chunk_sentences:
                if sentence in selected_sentences:
                    overlap_count += 1
            
            # Calculate overlap ratio
            total_sentences = len(chunk_sentences)
            if total_sentences == 0:
                continue
                
            overlap_ratio = overlap_count / total_sentences
            
            # Check if overlap exceeds threshold
            if overlap_ratio >= self.overlap_threshold:
                return True
        
        return False
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitting
        sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _extract_key_terms(self, text: str) -> set:
        """Extract key terms from text."""
        # Remove punctuation and convert to lowercase
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        
        # Remove stop words and split into terms
        stop_words = {
            'a', 'an', 'the', 'and', 'or', 'but', 'if', 'then', 'else', 'when',
            'at', 'by', 'for', 'with', 'about', 'against', 'between', 'into',
            'through', 'during', 'before', 'after', 'above', 'below', 'to', 'from',
            'up', 'down', 'in', 'out', 'on', 'off', 'over', 'under', 'again'
        }
        
        terms = set()
        for word in text.split():
            if word not in stop_words and len(word) > 3:
                terms.add(word)
        
        return terms
    
    def _count_tokens(self, text: str) -> int:
        """Count the number of tokens in text."""
        if self.tokenizer:
            # Use provided tokenizer
            return len(self.tokenizer.encode(text))
        else:
            # Approximate token count (roughly 4 chars per token for English)
            return len(text) // 4