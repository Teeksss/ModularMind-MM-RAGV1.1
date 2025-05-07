from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from typing import List, Optional, Dict, Any

from app.db.base_class import Base


class Document(Base):
    """Document model for storing uploaded documents."""
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=False)
    source = Column(String(500), nullable=True)
    language = Column(String(10), nullable=True)
    
    # Content stored separately for large documents
    content = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    
    # Metadata
    metadata = Column(JSON, nullable=True)
    
    # Tracking fields
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Ownership
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    
    # Status flags
    is_processed = Column(Boolean, default=False)
    is_indexed = Column(Boolean, default=False)
    is_public = Column(Boolean, default=False)
    
    # Enrichment status
    enrichment_status = Column(String(50), default="pending")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert document to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "content_type": self.content_type,
            "source": self.source,
            "language": self.language,
            "summary": self.summary,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "user_id": self.user_id,
            "is_processed": self.is_processed,
            "is_indexed": self.is_indexed,
            "is_public": self.is_public,
            "enrichment_status": self.enrichment_status,
            "chunks_count": len(self.chunks) if self.chunks else 0
        }


class DocumentChunk(Base):
    """Chunk of a document for efficient retrieval."""
    __tablename__ = "document_chunks"

    id = Column(String(36), primary_key=True, index=True)
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    metadata = Column(JSON, nullable=True)
    
    # Vector storage
    embedding_model = Column(String(100), nullable=True)
    embedding_vector = Column(Text, nullable=True)  # Base64 encoded vector
    
    # Relationships
    document = relationship("Document", back_populates="chunks")
    
    # Tracking
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert chunk to dictionary."""
        return {
            "id": self.id,
            "document_id": self.document_id,
            "chunk_index": self.chunk_index,
            "content": self.content,
            "metadata": self.metadata,
            "embedding_model": self.embedding_model,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }


class ChatSession(Base):
    """Chat session model for tracking chat history."""
    __tablename__ = "chat_sessions"

    id = Column(String(36), primary_key=True, index=True)
    title = Column(String(255), nullable=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    
    # Session metadata
    metadata = Column(JSON, nullable=True)
    
    # Tracking
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_activity = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "user_id": self.user_id,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_activity": self.last_activity,
            "messages_count": len(self.messages) if self.messages else 0
        }


class ChatMessage(Base):
    """Individual chat message within a session."""
    __tablename__ = "chat_messages"

    id = Column(String(36), primary_key=True, index=True)
    session_id = Column(String(36), ForeignKey("chat_sessions.id"), nullable=False)
    role = Column(String(50), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    
    # Message metadata
    metadata = Column(JSON, nullable=True)
    
    # Citations and sources
    citations = Column(JSON, nullable=True)
    
    # Tracking
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    session = relationship("ChatSession", back_populates="messages")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "metadata": self.metadata,
            "citations": self.citations,
            "created_at": self.created_at
        }