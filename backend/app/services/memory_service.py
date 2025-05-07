from typing import Dict, Any, List, Optional, Tuple
import logging
import asyncio
import time
import uuid
from datetime import datetime
import json
import redis.asyncio as redis

from app.core.settings import get_settings
from app.db.session import get_db

settings = get_settings()
logger = logging.getLogger(__name__)


class MemoryService:
    """
    Service for handling conversational memory and session management.
    
    Stores conversation history and provides context for queries.
    """
    
    def __init__(self):
        """Initialize the memory service."""
        self.ttl = settings.memory.memory_ttl_seconds
        self.max_history = settings.memory.memory_max_history_items
        
        # Initialize Redis client if enabled
        self.redis = None
        if settings.memory.memory_enabled:
            self._initialize_redis()
    
    def _initialize_redis(self):
        """Initialize Redis connection."""
        try:
            self.redis = redis.Redis(
                host=settings.redis.redis_host,
                port=settings.redis.redis_port,
                password=settings.redis.redis_password,
                db=settings.redis.redis_db,
                decode_responses=True
            )
            logger.info("Redis connection initialized for memory service")
        except Exception as e:
            logger.error(f"Failed to initialize Redis: {str(e)}")
            self.redis = None
    
    async def create_session(self, user_id: str) -> str:
        """
        Create a new session for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Session ID
        """
        session_id = str(uuid.uuid4())
        
        try:
            # Store in database
            async with get_db() as db:
                query = """
                INSERT INTO memory_sessions (id, user_id, created_at, last_used)
                VALUES ($1, $2, $3, $3)
                RETURNING id
                """
                
                values = (
                    session_id,
                    user_id,
                    datetime.now()
                )
                
                await db.execute(query, *values)
                
            # Initialize in Redis if available
            if self.redis:
                # Create session key
                session_key = f"session:{session_id}"
                await self.redis.hset(session_key, "user_id", user_id)
                await self.redis.hset(session_key, "created_at", datetime.now().isoformat())
                await self.redis.hset(session_key, "last_used", datetime.now().isoformat())
                
                # Set TTL
                await self.redis.expire(session_key, self.ttl)
            
            return session_id
            
        except Exception as e:
            logger.error(f"Error creating session: {str(e)}")
            raise
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session information.
        
        Args:
            session_id: Session ID
            
        Returns:
            Session information or None if not found
        """
        # Try Redis first
        if self.redis:
            try:
                session_key = f"session:{session_id}"
                session_data = await self.redis.hgetall(session_key)
                
                if session_data:
                    return session_data
            except Exception as e:
                logger.warning(f"Redis error getting session: {str(e)}")
        
        # Fall back to database
        try:
            async with get_db() as db:
                query = """
                SELECT id, user_id, created_at, last_used, metadata
                FROM memory_sessions
                WHERE id = $1
                """
                
                result = await db.fetch_one(query, session_id)
                
                if not result:
                    return None
                
                session = dict(result)
                
                # Convert metadata from JSON if needed
                if session.get("metadata") and isinstance(session["metadata"], str):
                    session["metadata"] = json.loads(session["metadata"])
                
                return session
                
        except Exception as e:
            logger.error(f"Error getting session: {str(e)}")
            return None
    
    async def update_session(self, session_id: str) -> bool:
        """
        Update session last used timestamp.
        
        Args:
            session_id: Session ID
            
        Returns:
            True if successful
        """
        now = datetime.now()
        
        # Update in Redis if available
        if self.redis:
            try:
                session_key = f"session:{session_id}"
                
                # Check if session exists
                exists = await self.redis.exists(session_key)
                if exists:
                    await self.redis.hset(session_key, "last_used", now.isoformat())
                    await self.redis.expire(session_key, self.ttl)
            except Exception as e:
                logger.warning(f"Redis error updating session: {str(e)}")
        
        # Update in database
        try:
            async with get_db() as db:
                query = """
                UPDATE memory_sessions
                SET last_used = $1
                WHERE id = $2
                RETURNING id
                """
                
                result = await db.fetch_one(query, now, session_id)
                
                return result is not None
                
        except Exception as e:
            logger.error(f"Error updating session: {str(e)}")
            return False
    
    async def add_to_session(
        self,
        session_id: str,
        type: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add an item to a session.
        
        Args:
            session_id: Session ID
            type: Item type (query, response, document, system)
            content: Item content
            metadata: Optional metadata
            
        Returns:
            Item ID
        """
        # Update session last used time
        await self.update_session(session_id)
        
        # Generate item ID
        item_id = str(uuid.uuid4())
        now = datetime.now()
        
        # Add to database
        try:
            async with get_db() as db:
                query = """
                INSERT INTO memory_items (id, session_id, type, content, metadata, created_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
                """
                
                values = (
                    item_id,
                    session_id,
                    type,
                    content,
                    json.dumps(metadata or {}),
                    now
                )
                
                await db.execute(query, *values)
            
            # Add to Redis if available
            if self.redis:
                try:
                    # Create item hash
                    item_key = f"item:{item_id}"
                    await self.redis.hset(item_key, "session_id", session_id)
                    await self.redis.hset(item_key, "type", type)
                    await self.redis.hset(item_key, "content", content)
                    await self.redis.hset(item_key, "metadata", json.dumps(metadata or {}))
                    await self.redis.hset(item_key, "created_at", now.isoformat())
                    
                    # Set TTL
                    await self.redis.expire(item_key, self.ttl)
                    
                    # Add to session items list
                    list_key = f"session:{session_id}:items"
                    await self.redis.lpush(list_key, item_id)
                    await self.redis.expire(list_key, self.ttl)
                    
                    # Trim list if needed
                    await self.redis.ltrim(list_key, 0, self.max_history - 1)
                    
                except Exception as e:
                    logger.warning(f"Redis error adding item: {str(e)}")
            
            return item_id
            
        except Exception as e:
            logger.error(f"Error adding to session: {str(e)}")
            raise
    
    async def get_session_items(
        self,
        session_id: str,
        limit: int = None,
        item_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get items from a session.
        
        Args:
            session_id: Session ID
            limit: Maximum number of items to retrieve
            item_type: Optional filter by item type
            
        Returns:
            List of session items
        """
        # Use class max_history if limit not provided
        if limit is None:
            limit = self.max_history
        
        # Try Redis first
        if self.redis:
            try:
                list_key = f"session:{session_id}:items"
                
                # Get item IDs from list
                item_ids = await self.redis.lrange(list_key, 0, limit - 1)
                
                if not item_ids:
                    # Fall back to database
                    pass
                else:
                    # Get items from Redis
                    items = []
                    
                    for item_id in item_ids:
                        item_key = f"item:{item_id}"
                        item_data = await self.redis.hgetall(item_key)
                        
                        if not item_data:
                            continue
                        
                        # Skip if type doesn't match
                        if item_type and item_data.get("type") != item_type:
                            continue
                        
                        # Parse metadata
                        if "metadata" in item_data:
                            try:
                                item_data["metadata"] = json.loads(item_data["metadata"])
                            except:
                                item_data["metadata"] = {}
                        
                        item_data["id"] = item_id
                        items.append(item_data)
                    
                    return items
            
            except Exception as e:
                logger.warning(f"Redis error getting items: {str(e)}")
        
        # Fall back to database
        try:
            async with get_db() as db:
                if item_type:
                    query = """
                    SELECT id, session_id, type, content, metadata, created_at
                    FROM memory_items
                    WHERE session_id = $1 AND type = $2
                    ORDER BY created_at DESC
                    LIMIT $3
                    """
                    results = await db.fetch_all(query, session_id, item_type, limit)
                else:
                    query = """
                    SELECT id, session_id, type, content, metadata, created_at
                    FROM memory_items
                    WHERE session_id = $1
                    ORDER BY created_at DESC
                    LIMIT $2
                    """
                    results = await db.fetch_all(query, session_id, limit)
                
                items = []
                for row in results:
                    item = dict(row)
                    
                    # Parse metadata from JSON
                    if item.get("metadata") and isinstance(item["metadata"], str):
                        item["metadata"] = json.loads(item["metadata"])
                    
                    items.append(item)
                
                return items
                
        except Exception as e:
            logger.error(f"Error getting session items: {str(e)}")
            return []
    
    async def get_session_context(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get session context for use in queries.
        
        Args:
            session_id: Session ID
            
        Returns:
            List of context items
        """
        # Get items from the session
        items = await self.get_session_items(session_id)
        
        # Return sorted by timestamp (oldest first)
        return sorted(items, key=lambda x: x.get('created_at', ''))
    
    async def clear_session(self, session_id: str) -> bool:
        """
        Clear all items from a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            True if successful
        """
        # Clear from Redis if available
        if self.redis:
            try:
                # Get item IDs
                list_key = f"session:{session_id}:items"
                item_ids = await self.redis.lrange(list_key, 0, -1)
                
                # Delete items
                for item_id in item_ids:
                    await self.redis.delete(f"item:{item_id}")
                
                # Delete list
                await self.redis.delete(list_key)
                
            except Exception as e:
                logger.warning(f"Redis error clearing session: {str(e)}")
        
        # Clear from database
        try:
            async with get_db() as db:
                query = """
                DELETE FROM memory_items
                WHERE session_id = $1
                """
                
                await db.execute(query, session_id)
                
                return True
                
        except Exception as e:
            logger.error(f"Error clearing session: {str(e)}")
            return False


# Create a singleton instance
_memory_service = MemoryService()

def get_memory_service() -> MemoryService:
    """Get the memory service singleton."""
    return _memory_service