from typing import Dict, Any, List, Optional, Tuple, Union, Set
import logging
import time
import math
import re
from collections import Counter, defaultdict
import json
import asyncio

from app.core.settings import get_settings
from app.services.retrievers.base import BaseRetriever, SearchResult
from app.db.session import get_db

settings = get_settings()
logger = logging.getLogger(__name__)


class BM25Retriever(BaseRetriever):
    """
    BM25 retriever for keyword-based search.
    
    Implements the BM25 algorithm for sparse retrieval based on keyword matching.
    Can be used standalone or as part of a hybrid retrieval system.
    """
    
    def __init__(
        self,
        k1: float = 1.5,
        b: float = 0.75,
        use_cache: bool = True,
        cache_ttl: int = 3600  # 1 hour
    ):
        """
        Initialize the BM25 retriever.
        
        Args:
            k1: Term frequency saturation parameter
            b: Document length normalization parameter
            use_cache: Whether to cache results
            cache_ttl: Cache TTL in seconds
        """
        self.k1 = k1
        self.b = b
        self.use_cache = use_cache
        self.cache_ttl = cache_ttl
        
        # Index data structures
        self.doc_lengths = {}  # {doc_id: length}
        self.avg_doc_length = 0.0
        self.term_frequencies = defaultdict(dict)  # {term: {doc_id: freq}}
        self.doc_frequencies = defaultdict(int)  # {term: num_docs_with_term}
        self.document_count = 0
        self.document_metadata = {}  # {doc_id: metadata}
        
        # Cache for queries
        self.query_cache = {}  # {query_hash: (timestamp, results)}
        
        # Tokenization and stopwords
        self.stopwords = self._load_stopwords()
        
        super().__init__()
        
        logger.info(
            f"Initialized BM25Retriever with k1={self.k1}, b={self.b}, "
            f"use_cache={self.use_cache}, cache_ttl={self.cache_ttl}"
        )
    
    async def initialize(self) -> None:
        """Initialize the BM25 retriever by building the index."""
        logger.info("Initializing BM25 retriever and building index")
        start_time = time.time()
        
        # Build the index
        await self._build_index()
        
        # Calculate average document length
        if self.document_count > 0:
            self.avg_doc_length = sum(self.doc_lengths.values()) / self.document_count
        
        init_time = time.time() - start_time
        logger.info(
            f"BM25 index built in {init_time:.2f}s with {self.document_count} documents and "
            f"{len(self.term_frequencies)} unique terms"
        )
    
    async def search(
        self,
        query: str,
        k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> List[SearchResult]:
        """
        Search using BM25 algorithm.
        
        Args:
            query: The search query
            k: Number of results to return
            filters: Optional filters to apply to the search
            **kwargs: Additional arguments
            
        Returns:
            List of search results
        """
        start_time = time.time()
        
        # Check cache first
        cache_key = self._get_cache_key(query, k, filters)
        cached_results = self._get_from_cache(cache_key)
        if cached_results:
            logger.debug(f"Returning cached results for query: {query}")
            return cached_results
        
        # Tokenize query
        query_terms = self._tokenize(query)
        
        # Get relevant documents (those containing at least one query term)
        relevant_docs = self._get_relevant_docs(query_terms)
        
        # Calculate BM25 scores
        doc_scores = {}
        for doc_id in relevant_docs:
            # Skip if doesn't match filters
            if filters and not self._matches_filters(doc_id, filters):
                continue
                
            score = self._calculate_bm25_score(query_terms, doc_id)
            doc_scores[doc_id] = score
        
        # Sort by score and get top k results
        sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)[:k]
        
        # Fetch document content for results
        results = []
        for doc_id, score in sorted_docs:
            # Get document content and metadata
            text = await self._get_document_text(doc_id)
            metadata = self.document_metadata.get(doc_id, {})
            
            # Add to results
            results.append(SearchResult(
                id=doc_id,
                text=text,
                score=score,
                metadata={
                    **metadata,
                    "retrieval_method": "bm25"
                }
            ))
        
        # Cache results
        if self.use_cache:
            self._add_to_cache(cache_key, results)
        
        processing_time = time.time() - start_time
        logger.info(f"BM25 search completed in {processing_time:.3f}s with {len(results)} results")
        
        return results
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into terms."""
        # Convert to lowercase and replace non-alphanumeric with spaces
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        
        # Split into tokens
        tokens = text.split()
        
        # Remove stopwords
        tokens = [token for token in tokens if token not in self.stopwords]
        
        return tokens
    
    def _get_relevant_docs(self, query_terms: List[str]) -> Set[str]:
        """Get documents that contain at least one query term."""
        relevant_docs = set()
        
        for term in query_terms:
            if term in self.term_frequencies:
                relevant_docs.update(self.term_frequencies[term].keys())
        
        return relevant_docs
    
    def _calculate_bm25_score(self, query_terms: List[str], doc_id: str) -> float:
        """Calculate BM25 score for a document."""
        score = 0.0
        doc_length = self.doc_lengths.get(doc_id, 0)
        
        for term in query_terms:
            # Skip terms not in the index
            if term not in self.term_frequencies:
                continue
            
            # Get term frequency in document
            term_freq = self.term_frequencies[term].get(doc_id, 0)
            if term_freq == 0:
                continue
            
            # Get document frequency
            doc_freq = self.doc_frequencies.get(term, 0)
            if doc_freq == 0:
                continue
            
            # Calculate IDF component
            idf = math.log((self.document_count - doc_freq + 0.5) / (doc_freq + 0.5) + 1.0)
            
            # Calculate TF component with saturation and document length normalization
            tf = term_freq * (self.k1 + 1) / (term_freq + self.k1 * (1 - self.b + self.b * doc_length / self.avg_doc_length))
            
            # Add to score
            score += idf * tf
        
        return score
    
    async def _build_index(self) -> None:
        """Build the BM25 index from documents in the database."""
        # Clear existing index data
        self.doc_lengths = {}
        self.term_frequencies = defaultdict(dict)
        self.doc_frequencies = defaultdict(int)
        self.document_count = 0
        self.document_metadata = {}
        
        # Fetch document chunks from database
        async with get_db() as db:
            query = """
            SELECT 
                id, document_id, content, metadata
            FROM 
                document_chunks
            """
            
            chunks = await db.fetch_all(query)
        
        # Process each chunk
        for chunk in chunks:
            doc_id = chunk['id']
            content = chunk['content']
            
            # Process metadata
            try:
                if isinstance(chunk['metadata'], str):
                    metadata = json.loads(chunk['metadata'])
                else:
                    metadata = chunk['metadata'] or {}
            except:
                metadata = {}
            
            # Store metadata
            self.document_metadata[doc_id] = {
                **metadata,
                "document_id": chunk['document_id']
            }
            
            # Tokenize content
            tokens = self._tokenize(content)
            
            # Update document length
            self.doc_lengths[doc_id] = len(tokens)
            
            # Count term frequencies
            term_counts = Counter(tokens)
            
            # Update index structures
            for term, count in term_counts.items():
                # Update term frequency
                self.term_frequencies[term][doc_id] = count
                
                # Update document frequency (once per document)
                self.doc_frequencies[term] += 1
            
            # Increment document count
            self.document_count += 1
    
    def _matches_filters(self, doc_id: str, filters: Dict[str, Any]) -> bool:
        """Check if a document matches the provided filters."""
        metadata = self.document_metadata.get(doc_id, {})
        
        for key, value in filters.items():
            # Handle special case for document_id
            if key == "document_id" and metadata.get("document_id") != value:
                return False
            
            # Handle list of values (OR condition)
            if isinstance(value, list):
                if key not in metadata or metadata[key] not in value:
                    return False
            # Handle exact match
            elif key in metadata and metadata[key] != value:
                return False
            # Handle missing field that was required
            elif key not in metadata:
                return False
        
        return True
    
    async def _get_document_text(self, doc_id: str) -> str:
        """Get the text content of a document."""
        async with get_db() as db:
            query = """
            SELECT content FROM document_chunks WHERE id = $1
            """
            result = await db.fetch_one(query, doc_id)
            
            if result:
                return result['content']
            
            return ""
    
    def _get_cache_key(self, query: str, k: int, filters: Optional[Dict[str, Any]]) -> str:
        """Create a cache key for a query."""
        # Normalize query
        normalized_query = query.lower().strip()
        
        # Create a string representation of filters
        filters_str = ""
        if filters:
            filters_str = json.dumps(filters, sort_keys=True)
        
        # Combine into a key
        key = f"{normalized_query}|{k}|{filters_str}"
        
        return key
    
    def _get_from_cache(self, cache_key: str) -> Optional[List[SearchResult]]:
        """Get results from cache if available and not expired."""
        if not self.use_cache:
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
        if not self.use_cache:
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
    
    def _load_stopwords(self) -> Set[str]:
        """Load stopwords for filtering."""
        # English stopwords
        stopwords = {
            "a", "an", "the", "and", "or", "but", "if", "then", "else", "when",
            "at", "by", "for", "with", "about", "against", "between", "into",
            "through", "during", "before", "after", "above", "below", "to", "from",
            "up", "down", "in", "out", "on", "off", "over", "under", "again",
            "further", "then", "once", "here", "there", "when", "where", "why",
            "how", "all", "any", "both", "each", "few", "more", "most", "other",
            "some", "such", "no", "nor", "not", "only", "own", "same", "so",
            "than", "too", "very", "s", "t", "can", "will", "just", "don", "don't",
            "should", "should've", "now", "d", "ll", "m", "o", "re", "ve", "y",
            "ain", "aren", "aren't", "couldn", "couldn't", "didn", "didn't",
            "doesn", "doesn't", "hadn", "hadn't", "hasn", "hasn't", "haven",
            "haven't", "isn", "isn't", "ma", "mightn", "mightn't", "mustn",
            "mustn't", "needn", "needn't", "shan", "shan't", "shouldn", "shouldn't",
            "wasn", "wasn't", "weren", "weren't", "won", "won't", "wouldn", "wouldn't"
        }
        
        # Turkish stopwords
        turkish_stopwords = {
            "acaba", "altı", "altmış", "ama", "bana", "bazı", "belki", "ben", "benden",
            "beni", "benim", "beş", "bin", "bir", "biri", "birkaç", "birkez", "birşey",
            "birşeyi", "biz", "bizden", "bize", "bizi", "bizim", "bu", "buna", "bunda",
            "bundan", "bunu", "bunun", "da", "daha", "dahi", "de", "defa", "diye", "doksan",
            "dokuz", "dolayı", "dolayısıyla", "dört", "elli", "en", "gibi", "hem", "hep",
            "hepsi", "her", "herhangi", "herkesin", "hiç", "iki", "ile", "ilgili", "ise",
            "işte", "itibaren", "itibariyle", "kadar", "karşın", "kez", "ki", "kim", "kimden",
            "kime", "kimi", "kırk", "milyar", "milyon", "mu", "mı", "nasıl", "ne", "neden",
            "nedenle", "nerde", "nerede", "nereye", "niye", "niçin", "on", "ona", "ondan",
            "onlar", "onlardan", "onlari", "onların", "onu", "otuz", "sanki", "sekiz",
            "seksen", "sen", "senden", "seni", "senin", "siz", "sizden", "size", "sizi",
            "sizin", "trilyon", "tüm", "ve", "veya", "ya", "yani", "yedi", "yetmiş", "yine",
            "yirmi", "yüz", "çok", "çünkü", "üç", "şey", "şeyden", "şeyi", "şeyler", "şu",
            "şuna", "şunda", "şundan", "şunu"
        }
        
        # Combine all stopwords
        return stopwords.union(turkish_stopwords)