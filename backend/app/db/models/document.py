from sqlalchemy import (
    Column, String, Text, DateTime, ForeignKey, 
    Integer, Boolean, JSON, Enum, Index, Float
)
from sqlalchemy.orm import relationship
import enum
from datetime import datetime

from app.db.base import Base


class EnrichmentStatusEnum(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class Document(Base):
    """
    Database model for documents stored in the system.
    
    Includes content, metadata, and relationship to enrichment data.
    """
    __tablename__ = "documents"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    content_type = Column(String, nullable=False)
    source = Column(String, nullable=True)
    owner_id = Column(String, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    language = Column(String, default="en")
    metadata = Column(JSON, default={})
    is_active = Column(Boolean, default=True)
    enrichment_status = Column(
        Enum(EnrichmentStatusEnum), 
        default=EnrichmentStatusEnum.PENDING
    )
    
    # Relationships
    owner = relationship("User", back_populates="documents")
    enrichments = relationship("DocumentEnrichment", back_populates="document", cascade="all, delete-orphan")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    
    # Indexes for performance
    __table_args__ = (
        Index("ix_documents_owner_created", owner_id, created_at.desc()),
        Index("ix_documents_language", language),
    )


class DocumentChunk(Base):
    """
    Represents a chunk of a document used for retrieval.
    
    Documents are split into chunks for more effective retrieval.
    """
    __tablename__ = "document_chunks"

    id = Column(String, primary_key=True, index=True)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    embedding_id = Column(String, nullable=True)  # ID in vector store
    metadata = Column(JSON, default={})
    
    # Relationships
    document = relationship("Document", back_populates="chunks")
    
    # Indexes
    __table_args__ = (
        Index("ix_document_chunks_document_id", document_id),
        Index("ix_document_chunks_document_index", document_id, chunk_index),
    )


class DocumentEnrichment(Base):
    """
    Stores enrichment data for documents.
    
    Each enrichment is categorized by type (summary, metadata, etc.)
    """
    __tablename__ = "document_enrichments"

    id = Column(String, primary_key=True, index=True)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    type = Column(String, nullable=False)  # summary, metadata, qa_pair, relations, etc.
    data = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    agent = Column(String, nullable=True)  # Agent that created this enrichment
    
    # Relationships
    document = relationship("Document", back_populates="enrichments")
    
    # Indexes
    __table_args__ = (
        Index("ix_document_enrichments_document_type", document_id, type),
    )


class SyntheticQA(Base):
    """
    Stores synthetic question-answer pairs generated from documents.
    
    These are used to enhance retrieval by providing additional context.
    """
    __tablename__ = "synthetic_qa"

    id = Column(String, primary_key=True, index=True)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    relevance_score = Column(Float, default=1.0)
    source_chunk_id = Column(String, ForeignKey("document_chunks.id"), nullable=True)
    embedding_id = Column(String, nullable=True)  # ID in vector store
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index("ix_synthetic_qa_document_id", document_id),
    )


class DocumentRelation(Base):
    """
    Stores relationships between documents or document concepts.
    
    Used for building knowledge graphs and enhancing contextual retrieval.
    """
    __tablename__ = "document_relations"

    id = Column(String, primary_key=True, index=True)
    source_id = Column(String, ForeignKey("documents.id"), nullable=False)
    target_id = Column(String, ForeignKey("documents.id"), nullable=True)
    relation_type = Column(String, nullable=False)  # references, similar, contradicts, etc.
    confidence = Column(Float, default=1.0)
    metadata = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # If target_id is null, these fields define a concept relation
    concept_name = Column(String, nullable=True)
    concept_value = Column(String, nullable=True)
    
    # Indexes
    __table_args__ = (
        Index("ix_document_relations_source", source_id),
        Index("ix_document_relations_target", target_id),
        Index("ix_document_relations_concept", concept_name, concept_value),
    )