"""
LLM API rotaları.
"""

import logging
from typing import Dict, List, Any, Optional, Union
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# API doğrulama
from ModularMind.API.main import validate_token

logger = logging.getLogger(__name__)

# Router
router = APIRouter(dependencies=[Depends(validate_token)])

# Modeller
class LLMCompletionRequest(BaseModel):
    prompt: str
    model: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    stop_sequences: Optional[List[str]] = None
    system_message: Optional[str] = None
    stream: bool = False

class LLMChatMessage(BaseModel):
    role: str
    content: str

class LLMChatRequest(BaseModel):
    messages: List[LLMChatMessage]
    model: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    stop_sequences: Optional[List[str]] = None
    stream: bool = False

class LLMCompletionResponse(BaseModel):
    text: str
    model: str

class LLMChatResponse(BaseModel):
    message: LLMChatMessage
    model: str

class LLMModelsResponse(BaseModel):
    models: List[Dict[str, Any]]

# Rotalar
@router.post("/complete", response_model=LLMCompletionResponse)
async def complete_text(request: Request, completion_request: LLMCompletionRequest):
    """
    LLM ile metin tamamlama.
    """
    llm_service = request.app.state.llm_service
    
    # Streaming kontrolü
    if completion_request.stream:
        async def stream_response():
            try:
                async for chunk in llm_service.stream_text(
                    completion_request.prompt,
                    completion_request.model,
                    completion_request.max_tokens,
                    completion_request.temperature,
                    completion_request.top_p,
                    completion_request.stop_sequences,
                    completion_request.system_message
                ):
                    yield f"data: {chunk}\n\n"
                
                yield "data: [DONE]\n\n"
            except Exception as e:
                logger.error(f"Streaming hatası: {str(e)}")
                yield f"data: Error: {str(e)}\n\n"
        
        return StreamingResponse(stream_response(), media_type="text/event-stream")
    
    try:
        # Metin tamamlama
        response_text = llm_service.generate_text(
            completion_request.prompt,
            completion_request.model,
            completion_request.max_tokens,
            completion_request.temperature,
            completion_request.top_p,
            completion_request.stop_sequences,
            completion_request.system_message
        )
        
        # Model ID'sini al
        model_id = completion_request.model
        if not model_id:
            model_ids = llm_service.model_manager.get_model_ids()
            model_id = model_ids[0] if model_ids else "unknown"
        
        return {"text": response_text, "model": model_id}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"LLM tamamlama hatası: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/chat", response_model=LLMChatResponse)
async def chat_completion(request: Request, chat_request: LLMChatRequest):
    """
    LLM ile sohbet tamamlama.
    """
    llm_service = request.app.state.llm_service
    
    # Messaging formatını dönüştür
    messages = [
        {"role": message.role, "content": message.content}
        for message in chat_request.messages
    ]
    
    # Streaming kontrolü
    if chat_request.stream:
        async def stream_response():
            try:
                async for chunk in llm_service.stream_chat(
                    messages,
                    chat_request.model,
                    chat_request.max_tokens,
                    chat_request.temperature,
                    chat_request.top_p,
                    chat_request.stop_sequences
                ):
                    yield f"data: {chunk}\n\n"
                
                yield "data: [DONE]\n\n"
            except Exception as e:
                logger.error(f"Chat streaming hatası: {str(e)}")
                yield f"data: Error: {str(e)}\n\n"
        
        return StreamingResponse(stream_response(), media_type="text/event-stream")
    
    try:
        # Sohbet tamamlama
        response_message = llm_service.generate_chat(
            messages,
            chat_request.model,
            chat_request.max_tokens,
            chat_request.temperature,
            chat_request.top_p,
            chat_request.stop_sequences
        )
        
        # Model ID'sini al
        model_id = chat_request.model
        if not model_id:
            model_ids = llm_service.model_manager.get_model_ids()
            model_id = model_ids[0] if model_ids else "unknown"
        
        return {
            "message": LLMChatMessage(role=response_message["role"], content=response_message["content"]),
            "model": model_id
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"LLM sohbet hatası: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.get("/models", response_model=LLMModelsResponse)
async def get_models(request: Request):
    """
    Kullanılabilir LLM modellerini listeler.
    """
    llm_service = request.app.state.llm_service
    
    try:
        models = llm_service.get_models()
        return {"models": models}
    except Exception as e:
        logger.error(f"Model listeleme hatası: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))