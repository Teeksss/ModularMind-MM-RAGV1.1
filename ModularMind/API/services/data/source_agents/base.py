"""
Base classes for data source agents.
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

class SourceAgentError(Exception):
    """Base exception for source agent errors"""
    pass

@dataclass
class SourceConfig:
    """Configuration for data sources"""
    
    type: str
    connection: Dict[str, Any] = field(default_factory=dict)
    options: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SourceConfig':
        """Create from dictionary"""
        return cls(
            type=data["type"],
            connection=data.get("connection", {}),
            options=data.get("options", {}),
            metadata=data.get("metadata", {})
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "type": self.type,
            "connection": self.connection,
            "options": self.options,
            "metadata": self.metadata
        }

@dataclass
class Document:
    """Document extracted from a data source"""
    
    id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    source_type: str = "unknown"
    source_id: Optional[str] = None

@dataclass
class ExtractResult:
    """Result of a data extraction operation"""
    
    success: bool
    documents: List[Document] = field(default_factory=list)
    error_message: Optional[str] = None
    stats: Dict[str, Any] = field(default_factory=dict)

class BaseSourceAgent(ABC):
    """Base class for all data source agents"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize source agent
        
        Args:
            config: Source configuration
        """
        self.config = SourceConfig.from_dict(config)
        self.initialized = False
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize the agent
        
        Returns:
            bool: True if initialized successfully
        """
        pass
    
    @abstractmethod
    def extract(self) -> ExtractResult:
        """
        Extract data from the source
        
        Returns:
            ExtractResult: Extraction result
        """
        pass
    
    @abstractmethod
    def validate_config(self) -> Tuple[bool, Optional[str]]:
        """
        Validate configuration
        
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        pass
    
    def get_source_type(self) -> str:
        """
        Get source type identifier
        
        Returns:
            str: Source type
        """
        return self.config.type
    
    def get_source_id(self) -> Optional[str]:
        """
        Get source identifier
        
        Returns:
            Optional[str]: Source ID or None
        """
        return self.config.metadata.get("id")
    
    def create_document_id(self, base_id: str) -> str:
        """
        Create a document ID from a base ID
        
        Args:
            base_id: Base identifier
            
        Returns:
            str: Document ID
        """
        source_id = self.get_source_id() or "unknown"
        source_type = self.get_source_type()
        
        # Format: source_type-source_id-base_id
        return f"{source_type}-{source_id}-{base_id}"
    
    def create_document(self, content: str, metadata: Dict[str, Any], base_id: str) -> Document:
        """
        Create a document
        
        Args:
            content: Document content
            metadata: Document metadata
            base_id: Base identifier
            
        Returns:
            Document: Created document
        """
        # Generate document ID
        doc_id = self.create_document_id(base_id)
        
        # Add source information to metadata
        doc_metadata = {
            "source_type": self.get_source_type(),
            "source_id": self.get_source_id(),
            "extraction_time": time.time()
        }
        
        # Add custom metadata
        doc_metadata.update(metadata)
        
        # Create document
        return Document(
            id=doc_id,
            content=content,
            metadata=doc_metadata,
            source_type=self.get_source_type(),
            source_id=self.get_source_id()
        )