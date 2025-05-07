from typing import Dict, Any, List, Optional, Tuple, Union
import logging
import time
import asyncio
from pydantic import BaseModel, Field

from app.core.settings import get_settings
from app.services.vector_store import get_vector_store
from app.services.retrievers.base import BaseRetriever, SearchResult
from app.services.retrievers.hybrid_retriever import HybridRetriever

settings = get_settings()
logger = logging.getLogger(__name__)


class MetadataFilter(BaseModel):
    """Model for metadata filters with comparison operations."""
    field: str
    operator: str  # equals, not_equals, gt, gte, lt, lte, in, not_in, exists, not_exists, contains
    value: Optional[Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for vector store."""
        if self.operator == "equals":
            return {self.field: self.value}
        elif self.operator == "not_equals":
            return {f"{self.field}!": self.value}
        elif self.operator == "gt":
            return {f"{self.field}>": self.value}
        elif self.operator == "gte":
            return {f"{self.field}>=": self.value}
        elif self.operator == "lt":
            return {f"{self.field}<": self.value}
        elif self.operator == "lte":
            return {f"{self.field}<=": self.value}
        elif self.operator == "in":
            return {f"{self.field}:": self.value}
        elif self.operator == "not_in":
            return {f"{self.field}!:": self.value}
        elif self.operator == "exists":
            return {f"{self.field}?": True}
        elif self.operator == "not_exists":
            return {f"{self.field}?": False}
        elif self.operator == "contains":
            return {f"{self.field}~": self.value}
        else:
            # Default to equals
            return {self.field: self.value}


class MetadataQuery(BaseModel):
    """Model for metadata-aware queries."""
    text: str
    filters: List[MetadataFilter] = Field(default_factory=list)
    filter_operator: str = "and"  # "and" or "or"
    boost_by: Optional[Dict[str, float]] = None
    order_by: Optional[List[str]] = None


class MetadataAwareRetriever(BaseRetriever):
    """
    Metadata-aware retriever that enhances retrieval with metadata filtering and boosting.
    
    Extends any base retriever with advanced metadata handling:
    - Filtering by metadata fields (equals, range, exists, etc.)
    - Boosting results by metadata values
    - Sorting results by metadata fields
    - Time-based and category-based filtering
    """
    
    def __init__(
        self,
        base_retriever: Optional[BaseRetriever] = None,
        apply_boosting: bool = True,
        apply_reweighting: bool = True,
        default_recency_factor: float = 0.2
    ):
        """
        Initialize the metadata-aware retriever.
        
        Args:
            base_retriever: Underlying retriever to use (defaults to HybridRetriever)
            apply_boosting: Whether to apply metadata-based score boosting
            apply_reweighting: Whether to reweight results by a combination of relevance and metadata
            default_recency_factor: Default factor for time-based recency boosting (0.0 to 1.0)
        """
        self.base_retriever = base_retriever or HybridRetriever()
        self.apply_boosting = apply_boosting
        self.apply_reweighting = apply_reweighting
        self.default_recency_factor = max(0.0, min(1.0, default_recency_factor))
        
        # Metadata field types for special handling
        self.date_fields = {"created_at", "updated_at", "publication_date", "timestamp"}
        self.category_fields = {"category", "type", "sector", "topic", "domain"}
        
        logger.info(
            f"Initialized MetadataAwareRetriever with base_retriever={type(base_retriever).__name__}, "
            f"apply_boosting={apply_boosting}, apply_reweighting={apply_reweighting}"
        )
    
    async def initialize(self) -> None:
        """Initialize the retriever."""
        # Initialize base retriever
        if self.base_retriever:
            await self.base_retriever.initialize()
    
    async def search(
        self,
        query: str,
        k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        metadata_query: Optional[MetadataQuery] = None,
        **kwargs
    ) -> List[SearchResult]:
        """
        Search with metadata awareness.
        
        Args:
            query: The search query
            k: Number of results to return
            filters: Basic filters (simple field equality)
            metadata_query: Advanced metadata query specification
            **kwargs: Additional arguments
            
        Returns:
            List of search results
        """
        start_time = time.time()
        
        # Process metadata query if provided
        if metadata_query is not None:
            processed_filters = self._process_metadata_query(metadata_query)
            # Merge with basic filters if provided
            if filters:
                processed_filters.update(filters)
            filters = processed_filters
        
        # Get boosting params from metadata query
        boost_by = metadata_query.boost_by if metadata_query else None
        order_by = metadata_query.order_by if metadata_query else None
        
        # Get more results than needed for post-filtering
        retrieve_k = k * 2
        
        # Perform base retrieval
        results = await self.base_retriever.search(
            query=query,
            k=retrieve_k,
            filters=filters,
            **kwargs
        )
        
        # Apply metadata-based post-processing
        if len(results) > 0:
            if self.apply_boosting and boost_by:
                results = self._apply_boosting(results, boost_by)
            
            if self.apply_reweighting:
                results = self._apply_reweighting(results, query)
            
            # Sort by order_by fields if specified
            if order_by:
                results = self._apply_ordering(results, order_by)
            else:
                # Default to sorting by score
                results = sorted(results, key=lambda x: x.score, reverse=True)
            
            # Limit to k results
            results = results[:k]
        
        processing_time = time.time() - start_time
        logger.info(
            f"Metadata-aware search completed in {processing_time:.3f}s with {len(results)} results"
        )
        
        return results
    
    def _process_metadata_query(self, metadata_query: MetadataQuery) -> Dict[str, Any]:
        """Process a metadata query into a filters dictionary."""
        if not metadata_query.filters:
            return {}
        
        # Process each filter into a dictionary
        filter_dicts = [filter.to_dict() for filter in metadata_query.filters]
        
        # Combine filters based on operator
        if metadata_query.filter_operator.lower() == "or":
            # OR operator requires special handling
            return {"$or": filter_dicts}
        else:
            # AND operator (default) - merge all dictionaries
            merged_filters = {}
            for filter_dict in filter_dicts:
                merged_filters.update(filter_dict)
            return merged_filters
    
    def _apply_boosting(self, results: List[SearchResult], boost_by: Dict[str, float]) -> List[SearchResult]:
        """Apply boosting to results based on metadata fields."""
        for result in results:
            original_score = result.score
            boost_score = 0.0
            
            # Apply boosts based on metadata fields
            for field, boost_value in boost_by.items():
                if field in result.metadata:
                    field_value = result.metadata[field]
                    
                    # Handle different field types
                    if field in self.date_fields:
                        # Date-based boost (more recent = higher score)
                        boost_score += self._calculate_recency_boost(field_value, boost_value)
                    elif field in self.category_fields and isinstance(field_value, str):
                        # Category-based boost (exact match = full boost)
                        if boost_by.get(f"{field}_value") == field_value:
                            boost_score += boost_value
                    else:
                        # Default boost (field exists = full boost)
                        boost_score += boost_value
            
            # Apply the boost with a weighted formula
            result.score = (0.7 * original_score) + (0.3 * boost_score)
            
            # Store original score in metadata
            result.metadata["original_score"] = original_score
            result.metadata["boost_score"] = boost_score
        
        return results
    
    def _apply_reweighting(self, results: List[SearchResult], query: str) -> List[SearchResult]:
        """Apply reweighting to results based on metadata and query."""
        # Check for time-based queries
        has_time_terms = self._check_for_time_terms(query)
        
        for result in results:
            # If query has time-related terms, boost documents with date metadata
            if has_time_terms:
                for date_field in self.date_fields:
                    if date_field in result.metadata:
                        # Apply a recency boost
                        recency_boost = self._calculate_recency_boost(
                            result.metadata[date_field], 
                            self.default_recency_factor
                        )
                        result.score = result.score * (1.0 + recency_boost)
                        break
        
        return results
    
    def _apply_ordering(self, results: List[SearchResult], order_by: List[str]) -> List[SearchResult]:
        """Apply ordering to results based on metadata fields."""
        for field in reversed(order_by):
            reverse_sort = False
            sort_field = field
            
            # Check for descending sort indicator
            if field.startswith("-"):
                reverse_sort = True
                sort_field = field[1:]
            
            # Sort by the field
            results = sorted(
                results,
                key=lambda x: self._get_sort_key(x.metadata, sort_field),
                reverse=reverse_sort
            )
        
        return results
    
    def _get_sort_key(self, metadata: Dict[str, Any], field: str) -> Any:
        """Get a sort key from metadata with a sensible default for missing values."""
        if field not in metadata:
            # Return a default value based on field type
            if field in self.date_fields:
                return "1970-01-01T00:00:00Z"  # Epoch start for dates
            elif field == "score":
                return 0.0
            else:
                return ""  # Empty string for text
        
        return metadata[field]
    
    def _calculate_recency_boost(self, date_value: Any, factor: float) -> float:
        """Calculate a recency boost based on a date value."""
        try:
            # Parse date if it's a string
            if isinstance(date_value, str):
                from datetime import datetime
                try:
                    # Try ISO format
                    date_obj = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
                except ValueError:
                    try:
                        # Try common format
                        date_obj = datetime.strptime(date_value, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        # If all fails, return 0 boost
                        return 0.0
                
                # Calculate age in days
                now = datetime.now().replace(tzinfo=date_obj.tzinfo)
                age_days = (now - date_obj).days
                
                # Exponential decay based on age
                if age_days < 0:
                    return 0.0
                
                # Max age for boosting (1 year)
                max_age = 365
                
                if age_days > max_age:
                    return 0.0
                
                # Calculate decay factor (newer = higher)
                decay = 1.0 - (age_days / max_age)
                
                return decay * factor
            
        except Exception as e:
            logger.debug(f"Error calculating recency boost: {str(e)}")
        
        return 0.0
    
    def _check_for_time_terms(self, query: str) -> bool:
        """Check if query contains time-related terms."""
        time_terms = {
            'recent', 'new', 'latest', 'current', 'today', 'yesterday', 'last week',
            'this month', 'this year', 'latest', 'newest', 'updated', 'just released',
            'modern', 'contemporary', 'now', 'present'
        }
        
        # Check for time terms in query
        query_terms = query.lower().split()
        return any(term in time_terms for term in query_terms)