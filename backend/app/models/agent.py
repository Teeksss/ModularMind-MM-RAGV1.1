from sqlalchemy import Column, String, DateTime, Boolean, Integer, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime
from uuid import uuid4
from typing import Optional, Dict, Any
from pydantic import BaseModel

class Agent(Base):
    __tablename__ = "agents"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    name = Column(String, nullable=False)
    description = Column(String)
    type = Column(String, nullable=False)  # rag, chat, etc.
    configuration = Column(JSON)
    status = Column(String, default="active")
    is_active = Column(Boolean, default=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime)
    total_tasks = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)
    
    # Relationships
    user = relationship("User", back_populates="agents")
    tasks = relationship("Task", back_populates="agent")

class AgentCreate(BaseModel):
    name: str
    description: Optional[str]
    type: str
    configuration: Dict[str, Any]

class AgentUpdate(BaseModel):
    name: Optional[str]
    description: Optional[str]
    configuration: Optional[Dict[str, Any]]
    status: Optional[str]
    is_active: Optional[bool]

class AgentResponse(BaseModel):
    status: str
    data: Optional[Dict[str, Any]]
    message: Optional[str]

class AgentList(BaseModel):
    status: str
    data: List[Dict[str, Any]]
    total: int
    skip: int
    limit: int