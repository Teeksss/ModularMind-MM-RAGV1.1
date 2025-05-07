from typing import Dict, Any, List, Optional, Union
import json
import logging
import os
import time
import asyncio
from enum import Enum
import httpx
from openai import AsyncOpenAI
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from pydantic import BaseModel, Field, validator

from app.core.settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    OPENAI = "openai"
    MISTRAL = "mistral"
    ANTHROPIC = "anthropic"
    LOCAL = "local"


class ChatMessage(BaseModel):
    """Chat message model."""
    role: str
    content: str


class CompletionRequest(BaseModel):
    """Generic request structure for completions across providers."""
    model: str = settings.llm.llm_model
    messages: List[ChatMessage]
    temperature: float = 0.0
    max_tokens: Optional[int] = None
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop: Optional[List[str]] = None
    stream: bool = False
    
    class Config:
        validate_assignment = True


class CompletionResponse(BaseModel):
    """Generic response structure for completions."""
    text: str
    model: str
    finish_reason: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    raw_response: Optional[Dict[str, Any]] = None


class TokenCount(BaseModel):
    """Token count information."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class LLMCallMetrics(BaseModel):
    """Metrics for LLM API calls."""
    calls: int = 0
    tokens: TokenCount = Field(default_factory=TokenCount)
    duration_ms: float = 0.0
    errors: int = 0
    last_called: Optional[float] = None
    
    def record_call(self, 
                   duration_ms: float, 
                   prompt_tokens: Optional[int] = None,
                   completion_tokens: Optional[int] = None,
                   total_tokens: Optional[int] = None):
        """Record a successful LLM call."""
        self.calls += 1
        self.duration_ms += duration_ms
        self.last_called = time.time()
        
        if prompt_tokens is not None:
            self.tokens.prompt_tokens += prompt_tokens
        if completion_tokens is not None:
            self.tokens.completion_tokens += completion_tokens
        if total_tokens is not None:
            self.tokens.total_tokens += total_tokens
    
    def record_error(self):
        """Record an error in LLM call."""
        self.errors += 1
        self.last_called = time.time()


class LLMService:
    """
    Service for interacting with Language Models (LLMs).
    
    Provides a unified interface to multiple LLM providers:
    - OpenAI
    - Mistral
    - Anthropic
    - Local (LLaMA, etc.)
    """
    
    def __init__(self):
        """Initialize LLM service with configured provider."""
        self.provider = LLMProvider(settings.llm.llm_provider)
        self.api_key = settings.llm.llm_api_key
        self.default_model = settings.llm.llm_model
        
        # Provider-specific clients
        self.openai_client = None
        self.mistral_client = None
        self.anthropic_client = None
        self.local_client = None
        
        # Initialize the appropriate client
        self._initialize_client()
        
        # Metrics
        self.metrics = LLMCallMetrics()
    
    def _initialize_client(self):
        """Initialize the appropriate client based on the provider."""
        if self.provider == LLMProvider.OPENAI:
            self.openai_client = AsyncOpenAI(api_key=self.api_key)
        
        elif self.provider == LLMProvider.MISTRAL:
            # Simple HTTP client for Mistral
            self.mistral_client = httpx.AsyncClient(
                base_url="https://api.mistral.ai/v1",
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
        
        elif self.provider == LLMProvider.ANTHROPIC:
            # Simple HTTP client for Anthropic
            self.anthropic_client = httpx.AsyncClient(
                base_url="https://api.anthropic.com/v1",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01"
                }
            )
        
        elif self.provider == LLMProvider.LOCAL:
            # HTTP client for local LLM server
            local_url = settings.llm.local_llm_server or "http://localhost:8080"
            self.local_client = httpx.AsyncClient(base_url=local_url)
    
    @retry(
        retry=retry_if_exception_type((httpx.RequestError, asyncio.TimeoutError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _generate_openai(self, request: CompletionRequest) -> CompletionResponse:
        """Generate text using OpenAI."""
        if not self.openai_client:
            self._initialize_client()
        
        start_time = time.time()
        
        try:
            messages = [{"role": m.role, "content": m.content} for m in request.messages]
            
            response = await self.openai_client.chat.completions.create(
                model=request.model,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                top_p=request.top_p,
                frequency_penalty=request.frequency_penalty,
                presence_penalty=request.presence_penalty,
                stop=request.stop,
                stream=request.stream
            )
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Extract token counts
            usage = response.usage
            prompt_tokens = usage.prompt_tokens if usage else None
            completion_tokens = usage.completion_tokens if usage else None
            total_tokens = usage.total_tokens if usage else None
            
            # Record metrics
            self.metrics.record_call(
                duration_ms=duration_ms,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens
            )
            
            # Return structured response
            return CompletionResponse(
                text=response.choices[0].message.content,
                model=response.model,
                finish_reason=response.choices[0].finish_reason,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                raw_response=response.model_dump()
            )
        
        except Exception as e:
            # Record error in metrics
            self.metrics.record_error()
            logger.error(f"Error in OpenAI call: {str(e)}")
            raise
    
    @retry(
        retry=retry_if_exception_type((httpx.RequestError, asyncio.TimeoutError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _generate_mistral(self, request: CompletionRequest) -> CompletionResponse:
        """Generate text using Mistral AI."""
        if not self.mistral_client:
            self._initialize_client()
        
        start_time = time.time()
        
        try:
            payload = {
                "model": request.model,
                "messages": [{"role": m.role, "content": m.content} for m in request.messages],
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
                "top_p": request.top_p
            }
            
            response = await self.mistral_client.post("/chat/completions", json=payload)
            response.raise_for_status()
            response_data = response.json()
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Extract token counts
            usage = response_data.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens")
            completion_tokens = usage.get("completion_tokens")
            total_tokens = usage.get("total_tokens")
            
            # Record metrics
            self.metrics.record_call(
                duration_ms=duration_ms,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens
            )
            
            # Return structured response
            return CompletionResponse(
                text=response_data["choices"][0]["message"]["content"],
                model=response_data["model"],
                finish_reason=response_data["choices"][0].get("finish_reason"),
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                raw_response=response_data
            )
        
        except Exception as e:
            # Record error in metrics
            self.metrics.record_error()
            logger.error(f"Error in Mistral call: {str(e)}")
            raise
    
    @retry(
        retry=retry_if_exception_type((httpx.RequestError, asyncio.TimeoutError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _generate_anthropic(self, request: CompletionRequest) -> CompletionResponse:
        """Generate text using Anthropic (Claude)."""
        if not self.anthropic_client:
            self._initialize_client()
        
        start_time = time.time()
        
        try:
            # Convert chat format to Anthropic format
            messages = []
            for msg in request.messages:
                if msg.role == "system":
                    # For Claude, we add the system message as a human message at the beginning
                    messages.append({"role": "human", "content": f"<system>\n{msg.content}\n</system>"})
                else:
                    role = "assistant" if msg.role == "assistant" else "human"
                    messages.append({"role": role, "content": msg.content})
            
            payload = {
                "model": request.model,
                "messages": messages,
                "max_tokens": request.max_tokens or 4096,
                "temperature": request.temperature,
                "top_p": request.top_p
            }
            
            response = await self.anthropic_client.post("/messages", json=payload)
            response.raise_for_status()
            response_data = response.json()
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Extract token counts if available
            usage = response_data.get("usage", {})
            input_tokens = usage.get("input_tokens")
            output_tokens = usage.get("output_tokens")
            total_tokens = (input_tokens or 0) + (output_tokens or 0)
            
            # Record metrics
            self.metrics.record_call(
                duration_ms=duration_ms,
                prompt_tokens=input_tokens,
                completion_tokens=output_tokens,
                total_tokens=total_tokens
            )
            
            # Return structured response
            return CompletionResponse(
                text=response_data["content"][0]["text"],
                model=response_data["model"],
                finish_reason=response_data.get("stop_reason"),
                prompt_tokens=input_tokens,
                completion_tokens=output_tokens,
                total_tokens=total_tokens,
                raw_response=response_data
            )
        
        except Exception as e:
            # Record error in metrics
            self.metrics.record_error()
            logger.error(f"Error in Anthropic call: {str(e)}")
            raise
    
    @retry(
        retry=retry_if_exception_type((httpx.RequestError, asyncio.TimeoutError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _generate_local(self, request: CompletionRequest) -> CompletionResponse:
        """Generate text using local LLM server."""
        if not self.local_client:
            self._initialize_client()
        
        start_time = time.time()
        
        try:
            # Adjust payload based on the local LLM server's API
            # This example assumes a simple API compatible with llama.cpp server
            messages_text = ""
            for msg in request.messages:
                if msg.role == "system":
                    messages_text += f"<|system|>\n{msg.content}\n"
                elif msg.role == "user":
                    messages_text += f"<|user|>\n{msg.content}\n"
                elif msg.role == "assistant":
                    messages_text += f"<|assistant|>\n{msg.content}\n"
            
            messages_text += "<|assistant|>\n"
            
            payload = {
                "prompt": messages_text,
                "temperature": request.temperature,
                "max_tokens": request.max_tokens or 2048,
                "stop": request.stop or ["<|user|>", "<|system|>"]
            }
            
            response = await self.local_client.post("/completion", json=payload)
            response.raise_for_status()
            response_data = response.json()
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Record metrics (local LLM might not provide token counts)
            self.metrics.record_call(duration_ms=duration_ms)
            
            # Return structured response
            return CompletionResponse(
                text=response_data["content"],
                model=settings.llm.local_llm_model_id or "local-model",
                finish_reason=response_data.get("stop_reason", "length"),
                raw_response=response_data
            )
        
        except Exception as e:
            # Record error in metrics
            self.metrics.record_error()
            logger.error(f"Error in local LLM call: {str(e)}")
            raise
    
    async def generate(self, 
                      prompt: str, 
                      model: Optional[str] = None,
                      system_prompt: Optional[str] = None,
                      temperature: float = 0.0,
                      max_tokens: Optional[int] = None) -> str:
        """
        Generate text from a prompt using the configured LLM.
        
        Args:
            prompt: The user prompt
            model: Optional model override
            system_prompt: Optional system prompt
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text
        """
        messages = []
        
        # Add system message if provided
        if system_prompt:
            messages.append(ChatMessage(role="system", content=system_prompt))
        
        # Add user message
        messages.append(ChatMessage(role="user", content=prompt))
        
        # Create request
        request = CompletionRequest(
            model=model or self.default_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        # Generate based on provider
        if self.provider == LLMProvider.OPENAI:
            response = await self._generate_openai(request)
        elif self.provider == LLMProvider.MISTRAL:
            response = await self._generate_mistral(request)
        elif self.provider == LLMProvider.ANTHROPIC:
            response = await self._generate_anthropic(request)
        elif self.provider == LLMProvider.LOCAL:
            response = await self._generate_local(request)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")
        
        return response.text
    
    async def generate_with_history(self,
                                  messages: List[Dict[str, str]],
                                  model: Optional[str] = None,
                                  temperature: float = 0.0,
                                  max_tokens: Optional[int] = None) -> str:
        """
        Generate text with a chat history.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Optional model override
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text
        """
        # Convert dict messages to ChatMessage objects
        chat_messages = [
            ChatMessage(role=msg["role"], content=msg["content"])
            for msg in messages
        ]
        
        # Create request
        request = CompletionRequest(
            model=model or self.default_model,
            messages=chat_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        # Generate based on provider
        if self.provider == LLMProvider.OPENAI:
            response = await self._generate_openai(request)
        elif self.provider == LLMProvider.MISTRAL:
            response = await self._generate_mistral(request)
        elif self.provider == LLMProvider.ANTHROPIC:
            response = await self._generate_anthropic(request)
        elif self.provider == LLMProvider.LOCAL:
            response = await self._generate_local(request)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")
        
        return response.text
    
    async def generate_json(self,
                           prompt: str,
                           model: Optional[str] = None,
                           system_prompt: Optional[str] = "You are a helpful assistant that always responds in valid JSON format.",
                           temperature: float = 0.0,
                           max_tokens: Optional[int] = None) -> Dict[str, Any]:
        """
        Generate JSON response from a prompt.
        
        Args:
            prompt: The user prompt
            model: Optional model override
            system_prompt: Optional system prompt
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated JSON as dict
        """
        # Add JSON instruction to prompt if not already included
        if "JSON" not in prompt and "json" not in prompt:
            prompt += "\n\nRespond with valid JSON only."
        
        response_text = await self.generate(
            prompt=prompt,
            model=model,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # Extract JSON from response if needed
        try:
            # Try to parse the whole response as JSON
            return json.loads(response_text)
        except json.JSONDecodeError:
            # If that fails, try to extract JSON from the response
            try:
                # Look for JSON-like content between curly braces
                json_content = response_text[response_text.find('{'):response_text.rfind('}')+1]
                return json.loads(json_content)
            except (json.JSONDecodeError, ValueError):
                # If all parsing attempts fail, return error info
                logger.error(f"Failed to parse JSON from response: {response_text}")
                return {
                    "error": "Failed to parse JSON response",
                    "raw_response": response_text
                }
    
    def get_metrics(self) -> LLMCallMetrics:
        """Get current metrics for LLM calls."""
        return self.metrics


# Create a singleton instance
_llm_service = LLMService()

def get_llm_service() -> LLMService:
    """Get the LLM service singleton."""
    return _llm_service