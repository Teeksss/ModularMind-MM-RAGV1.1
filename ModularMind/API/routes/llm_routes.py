"""
LLM API rotaları.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from ModularMind.API.main import get_llm_service, verify_token

router = APIRouter()

class CompletionRequest(BaseModel):
    """Metin tamamlama isteği modeli."""
    prompt: str
    model: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    stop_sequences: Optional[List[str]] = None
    system_message: Optional[str] = None
    stream: bool = False
    options: Optional[Dict[str, Any]] = None

class ChatCompletionRequest(BaseModel):
    """Sohbet tamamlama isteği modeli."""
    messages: List[Dict[str, str]]
    model: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    stop_sequences: Optional[List[str]] = None
    stream: bool = False
    options: Optional[Dict[str, Any]] = None

class TemplateCompletionRequest(BaseModel):
    """Şablon tamamlama isteği modeli."""
    template_id: str
    variables: Dict[str, str]
    model: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    options: Optional[Dict[str, Any]] = None

class CompletionResponse(BaseModel):
    """Metin tamamlama yanıtı modeli."""
    text: str
    model: str

class ChatCompletionResponse(BaseModel):
    """Sohbet tamamlama yanıtı modeli."""
    message: Dict[str, str]
    model: str

class TemplateCompletionResponse(BaseModel):
    """Şablon tamamlama yanıtı modeli."""
    text: str
    model: str
    template_id: str

class ModelsResponse(BaseModel):
    """Modeller yanıtı modeli."""
    models: List[Dict[str, Any]]

class TemplatesResponse(BaseModel):
    """Şablonlar yanıtı modeli."""
    templates: List[Dict[str, Any]]

class MetricsResponse(BaseModel):
    """Metrikler yanıtı modeli."""
    metrics: Dict[str, Any]

@router.post("/complete", response_model=CompletionResponse, dependencies=[Depends(verify_token)])
async def complete_text(request: CompletionRequest, llm_service=Depends(get_llm_service)):
    """
    Metinden metin üretir.
    """
    if request.stream:
        return StreamingResponse(
            _stream_text_generation(request, llm_service),
            media_type="text/event-stream"
        )
    
    try:
        text = llm_service.generate_text(
            prompt=request.prompt,
            model=request.model,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            top_p=request.top_p,
            stop_sequences=request.stop_sequences,
            system_message=request.system_message,
            options=request.options
        )
        
        model_used = request.model or llm_service.default_model
        
        return {
            "text": text,
            "model": model_used
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def _stream_text_generation(request, llm_service):
    """
    Metin üretimini stream olarak gönderir.
    """
    buffer = ""
    
    async def callback(chunk):
        nonlocal buffer
        buffer += chunk
        yield f"data: {chunk}\n\n"
    
    try:
        text = llm_service.generate_text(
            prompt=request.prompt,
            model=request.model,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            top_p=request.top_p,
            stop_sequences=request.stop_sequences,
            system_message=request.system_message,
            streaming_callback=callback,
            options=request.options
        )
        
        yield f"data: [DONE]\n\n"
    except Exception as e:
        yield f"data: [ERROR] {str(e)}\n\n"

@router.post("/chat", response_model=ChatCompletionResponse, dependencies=[Depends(verify_token)])
async def chat_completion(request: ChatCompletionRequest, llm_service=Depends(get_llm_service)):
    """
    Sohbet tamamlama yapar.
    """
    if request.stream:
        return StreamingResponse(
            _stream_chat_completion(request, llm_service),
            media_type="text/event-stream"
        )
    
    try:
        response = llm_service.chat_completion(
            messages=request.messages,
            model=request.model,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            top_p=request.top_p,
            stop_sequences=request.stop_sequences,
            options=request.options
        )
        
        model_used = request.model or llm_service.default_model
        
        return {
            "message": response,
            "model": model_used
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def _stream_chat_completion(request, llm_service):
    """
    Sohbet tamamlamasını stream olarak gönderir.
    """
    buffer = ""
    
    async def callback(chunk):
        nonlocal buffer
        buffer += chunk
        yield f"data: {chunk}\n\n"
    
    try:
        response = llm_service.chat_completion(
            messages=request.messages,
            model=request.model,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            top_p=request.top_p,
            stop_sequences=request.stop_sequences,
            streaming_callback=callback,
            options=request.options
        )
        
        yield f"data: [DONE]\n\n"
    except Exception as e:
        yield f"data: [ERROR] {str(e)}\n\n"

@router.post("/template", response_model=TemplateCompletionResponse, dependencies=[Depends(verify_token)])
async def template_completion(request: TemplateCompletionRequest, llm_service=Depends(get_llm_service)):
    """
    Şablondan metin üretir.
    """
    try:
        text = llm_service.generate_from_template(
            template_id=request.template_id,
            variables=request.variables,
            model=request.model,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            options=request.options
        )
        
        model_used = request.model or llm_service.default_model
        
        return {
            "text": text,
            "model": model_used,
            "template_id": request.template_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/models", response_model=ModelsResponse, dependencies=[Depends(verify_token)])
async def get_models(llm_service=Depends(get_llm_service)):
    """
    Mevcut LLM modellerini listeler.
    """
    try:
        models = llm_service.get_available_models()
        return {"models": models}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/templates", response_model=TemplatesResponse, dependencies=[Depends(verify_token)])
async def get_templates(llm_service=Depends(get_llm_service)):
    """
    Mevcut şablonları listeler.
    """
    try:
        templates = llm_service.get_available_templates()
        return {"templates": templates}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/metrics", response_model=MetricsResponse, dependencies=[Depends(verify_token)])
async def get_metrics(llm_service=Depends(get_llm_service)):
    """
    LLM servis metriklerini döndürür.
    """
    try:
        metrics = llm_service.get_metrics()
        return {"metrics": metrics}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))