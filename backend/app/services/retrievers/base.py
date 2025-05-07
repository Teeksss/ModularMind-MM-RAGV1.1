from typing import Dict, Any, List, Optional
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    """Class for search results from retrievers."""
    id: str
    text: str
    score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseRetriever(ABC):
    """
    Base class for retrievers.
    
    Defines the common interface for all retriever implementations.
    """
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the retriever."""
        pass
    
    @abstractmethod
    async def search(
        self,
        query: str,
        k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> List[SearchResult]:
        """
        Search for relevant documents.
        
        Args:
            query: The search query
            k: Number of results to return
            filters: Optional filters to apply to the search
            **kwargs: Additional arguments that might be needed by specific retrievers
            
        Returns:
            List of search results
        """
        pass