from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends, HTTPException
from typing import Dict, Any, List, Optional
import json
import logging
import asyncio
import uuid
from datetime import datetime

from app.api.deps import get_current_user, create_access_token
from app.models.user import User
from app.core.settings import get_settings
from app.services.query_service import get_query_service
from app.services.memory_service import get_memory_service

settings = get_settings()
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["WebSockets"])

# Store active connections
active_connections: Dict[str, WebSocket] = {}


class ConnectionManager:
    """
    Manager for WebSocket connections.
    
    Handles connection lifecycle and message broadcasting.
    """
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """Connect a WebSocket client."""
        await websocket.accept()
        active_connections[client_id] = websocket
        logger.info(f"Client connected: {client_id}")
    
    async def disconnect(self, client_id: str):
        """Disconnect a WebSocket client."""
        if client_id in active_connections:
            del active_connections[client_id]
            logger.info(f"Client disconnected: {client_id}")
    
    async def send_message(self, client_id: str, message: Dict[str, Any]):
        """Send a message to a specific client."""
        if client_id in active_connections:
            websocket = active_connections[client_id]
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message to client {client_id}: {str(e)}")
                await self.disconnect(client_id)
    
    async def broadcast(self, message: Dict[str, Any], exclude: Optional[List[str]] = None):
        """Broadcast a message to all connected clients, with optional exclusions."""
        exclude = exclude or []
        for client_id, websocket in list(active_connections.items()):
            if client_id not in exclude:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(f"Error broadcasting to client {client_id}: {str(e)}")
                    await self.disconnect(client_id)


manager = ConnectionManager()


@router.websocket("/")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(None),
    session_id: str = Query(None)
):
    """
    WebSocket endpoint for real-time communication.
    
    Requires authentication via token parameter.
    """
    # Authenticate the token
    try:
        import jwt
        from jwt.exceptions import PyJWTError
        
        payload = jwt.decode(token, settings.security.secret_key, algorithms=["HS256"])
        username: str = payload.get("sub")
        
        if not username:
            await websocket.close(code=1008, reason="Invalid token")
            return
        
    except PyJWTError:
        await websocket.close(code=1008, reason="Invalid token")
        return
    
    # Generate a unique client ID
    client_id = str(uuid.uuid4())
    
    # Initialize query service and memory service
    query_service = get_query_service()
    memory_service = get_memory_service()
    
    # Connect the client
    await manager.connect(websocket, client_id)
    
    try:
        # Send initial connection success message
        await manager.send_message(client_id, {
            "type": "connection_established",
            "client_id": client_id,
            "timestamp": datetime.now().isoformat()
        })
        
        # Main message handling loop
        while True:
            # Wait for messages from the client
            raw_data = await websocket.receive_text()
            
            try:
                data = json.loads(raw_data)
                
                # Handle different message types
                message_type = data.get("type")
                
                if message_type == "ping":
                    # Respond to ping with pong
                    await manager.send_message(client_id, {
                        "type": "pong",
                        "timestamp": datetime.now().isoformat()
                    })
                
                elif message_type == "query":
                    # Process a query
                    query_text = data.get("query")
                    query_session_id = data.get("session_id") or session_id
                    language = data.get("language", settings.multilingual.default_language)
                    
                    if not query_text:
                        await manager.send_message(client_id, {
                            "type": "error",
                            "error": "Missing query text",
                            "timestamp": datetime.now().isoformat()
                        })
                        continue
                    
                    # Acknowledge receipt of query
                    await manager.send_message(client_id, {
                        "type": "query_received",
                        "query": query_text,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    # Process the query in the background
                    asyncio.create_task(
                        process_query(
                            client_id=client_id,
                            query=query_text,
                            session_id=query_session_id,
                            language=language,
                            username=username
                        )
                    )
                
                elif message_type == "memory_request":
                    # Handle memory-related requests
                    memory_action = data.get("action")
                    
                    if memory_action == "get_items":
                        # Get memory items for a session
                        memory_session_id = data.get("session_id") or session_id
                        
                        if not memory_session_id:
                            await manager.send_message(client_id, {
                                "type": "error",
                                "error": "Missing session_id",
                                "timestamp": datetime.now().isoformat()
                            })
                            continue
                        
                        # Get memory items
                        items = await memory_service.get_session_items(memory_session_id)
                        
                        await manager.send_message(client_id, {
                            "type": "memory_items",
                            "session_id": memory_session_id,
                            "items": [dict(item) for item in items],
                            "timestamp": datetime.now().isoformat()
                        })
                
                else:
                    # Unknown message type
                    await manager.send_message(client_id, {
                        "type": "error",
                        "error": f"Unknown message type: {message_type}",
                        "timestamp": datetime.now().isoformat()
                    })
            
            except json.JSONDecodeError:
                # Invalid JSON
                await manager.send_message(client_id, {
                    "type": "error",
                    "error": "Invalid JSON message",
                    "timestamp": datetime.now().isoformat()
                })
            
            except Exception as e:
                # Other errors
                logger.error(f"Error processing message: {str(e)}", exc_info=True)
                await manager.send_message(client_id, {
                    "type": "error",
                    "error": "Internal server error",
                    "timestamp": datetime.now().isoformat()
                })
    
    except WebSocketDisconnect:
        # Client disconnected
        await manager.disconnect(client_id)
    
    except Exception as e:
        # Unexpected error
        logger.error(f"WebSocket error: {str(e)}", exc_info=True)
        await manager.disconnect(client_id)


async def process_query(
    client_id: str,
    query: str,
    session_id: Optional[str],
    language: str,
    username: str
):
    """
    Process a query from a WebSocket client.
    
    Args:
        client_id: The client ID
        query: The query text
        session_id: Optional session ID
        language: Query language
        username: Username of the client
    """
    try:
        # Get services
        query_service = get_query_service()
        memory_service = get_memory_service()
        
        # Get user ID from username
        # In a real implementation, this would use a more efficient lookup
        from app.api.deps import get_user_by_username
        user = await get_user_by_username(username)
        
        if not user:
            await manager.send_message(client_id, {
                "type": "error",
                "error": "User not found",
                "timestamp": datetime.now().isoformat()
            })
            return
        
        # Create a session if none provided
        if not session_id:
            session_id = await memory_service.create_session(user.id)
        
        # Send processing status
        await manager.send_message(client_id, {
            "type": "query_processing",
            "query": query,
            "timestamp": datetime.now().isoformat()
        })
        
        # Get context from memory if available
        context = await memory_service.get_session_context(session_id)
        
        # Process the query
        result = await query_service.process_query(
            query=query,
            user_id=user.id,
            session_id=session_id,
            language=language,
            max_results=5,
            include_sources=True,
            context=context
        )
        
        # Add to memory
        if result:
            await memory_service.add_to_session(
                session_id=session_id,
                type="query",
                content=query,
                metadata={"query_id": result.query_id}
            )
            
            await memory_service.add_to_session(
                session_id=session_id,
                type="response",
                content=result.answer,
                metadata={
                    "query_id": result.query_id,
                    "sources": [s.id for s in result.sources]
                }
            )
        
        # Send the result
        await manager.send_message(client_id, {
            "type": "query_result",
            "query": query,
            "result": {
                "answer": result.answer,
                "sources": [dict(s) for s in result.sources],
                "processing_time": result.processing_time
            },
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}", exc_info=True)
        
        # Send error message
        await manager.send_message(client_id, {
            "type": "query_error",
            "query": query,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        })