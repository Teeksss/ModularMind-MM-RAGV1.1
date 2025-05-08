"""
Centralized HTTP exception handling
"""
from typing import Any, Dict, Optional, Type, Union, List, Callable
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import http_exception_handler as fastapi_http_exception_handler
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
import json
import traceback
import time
from datetime import datetime

logger = logging.getLogger(__name__)

class ErrorDetail:
    """Error detail model for standardized error responses"""
    
    def __init__(
        self,
        message: str,
        code: str,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        exception: Optional[Exception] = None,
        request_id: Optional[str] = None
    ):
        self.message = message
        self.code = code
        self.details = details
        self.status_code = status_code
        self.exception = exception
        self.request_id = request_id
        self.timestamp = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error detail to dictionary"""
        result = {
            "error": {
                "message": self.message,
                "code": self.code,
                "timestamp": self.timestamp
            }
        }
        
        if self.request_id:
            result["error"]["request_id"] = self.request_id
            
        if self.details:
            result["error"]["details"] = self.details
            
        return result


class HTTPExceptionHandler:
    """Centralized HTTP exception handler for the API"""
    
    def __init__(self, app: FastAPI, debug: bool = False):
        """Initialize the exception handler and register it with the FastAPI app"""
        self.app = app
        self.debug = debug
        self.error_handlers: Dict[Type[Exception], Callable] = {}
        
        # Register default exception handlers
        self._register_default_handlers()
    
    def _register_default_handlers(self) -> None:
        """Register default exception handlers"""
        # Register Starlette HTTPException handler
        self.app.add_exception_handler(
            StarletteHTTPException,
            self._handle_http_exception
        )
        
        # Register RequestValidationError handler
        self.app.add_exception_handler(
            RequestValidationError,
            self._handle_validation_error
        )
        
        # Register Pydantic ValidationError handler
        self.app.add_exception_handler(
            ValidationError,
            self._handle_pydantic_validation_error
        )
        
        # Register general exception handler
        self.app.add_exception_handler(
            Exception,
            self._handle_general_exception
        )
    
    def register_exception_handler(
        self,
        exc_class: Type[Exception],
        handler: Callable[[Request, Exception], JSONResponse]
    ) -> None:
        """
        Register a custom exception handler for a specific exception class
        
        Args:
            exc_class: The exception class to handle
            handler: The handler function to use
        """
        self.app.add_exception_handler(exc_class, handler)
        self.error_handlers[exc_class] = handler
    
    async def _handle_http_exception(
        self,
        request: Request,
        exc: StarletteHTTPException
    ) -> JSONResponse:
        """
        Handle Starlette HTTPException
        
        Args:
            request: The request that caused the exception
            exc: The HTTPException
            
        Returns:
            JSONResponse: The error response
        """
        request_id = request.headers.get("X-Request-ID")
        
        # For some status codes, we want to customize the code
        code_map = {
            status.HTTP_401_UNAUTHORIZED: "unauthorized",
            status.HTTP_403_FORBIDDEN: "forbidden",
            status.HTTP_404_NOT_FOUND: "not_found",
            status.HTTP_429_TOO_MANY_REQUESTS: "rate_limit_exceeded"
        }
        
        code = code_map.get(exc.status_code, f"http_{exc.status_code}")
        
        # Log the exception with request details
        logger.warning(
            f"HTTP Exception: {exc.status_code} {exc.detail} - "
            f"Request: {request.method} {request.url.path}"
        )
        
        error_detail = ErrorDetail(
            message=str(exc.detail),
            code=code,
            status_code=exc.status_code,
            exception=exc,
            request_id=request_id
        )
        
        return JSONResponse(
            status_code=exc.status_code,
            content=error_detail.to_dict(),
            headers=getattr(exc, "headers", None)
        )
    
    async def _handle_validation_error(
        self,
        request: Request,
        exc: RequestValidationError
    ) -> JSONResponse:
        """
        Handle FastAPI RequestValidationError
        
        Args:
            request: The request that caused the exception
            exc: The validation error
            
        Returns:
            JSONResponse: The error response
        """
        request_id = request.headers.get("X-Request-ID")
        
        # Format validation errors
        error_details = []
        for error in exc.errors():
            error_details.append({
                "location": error["loc"],
                "message": error["msg"],
                "type": error["type"]
            })
        
        # Log the exception
        logger.warning(
            f"Validation error: {len(error_details)} errors - "
            f"Request: {request.method} {request.url.path}"
        )
        
        error_detail = ErrorDetail(
            message="Request validation error",
            code="validation_error",
            details={"errors": error_details},
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            exception=exc,
            request_id=request_id
        )
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error_detail.to_dict()
        )
    
    async def _handle_pydantic_validation_error(
        self,
        request: Request,
        exc: ValidationError
    ) -> JSONResponse:
        """
        Handle Pydantic ValidationError
        
        Args:
            request: The request that caused the exception
            exc: The validation error
            
        Returns:
            JSONResponse: The error response
        """
        request_id = request.headers.get("X-Request-ID")
        
        # Format validation errors
        error_details = []
        for error in exc.errors():
            error_details.append({
                "location": error["loc"],
                "message": error["msg"],
                "type": error["type"]
            })
        
        # Log the exception
        logger.warning(
            f"Pydantic validation error: {len(error_details)} errors - "
            f"Request: {request.method} {request.url.path}"
        )
        
        error_detail = ErrorDetail(
            message="Data validation error",
            code="validation_error",
            details={"errors": error_details},
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            exception=exc,
            request_id=request_id
        )
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error_detail.to_dict()
        )
    
    async def _handle_general_exception(
        self,
        request: Request,
        exc: Exception
    ) -> JSONResponse:
        """
        Handle any unhandled exception
        
        Args:
            request: The request that caused the exception
            exc: The exception
            
        Returns:
            JSONResponse: The error response
        """
        request_id = request.headers.get("X-Request-ID")
        
        # Get the full exception traceback
        tb = traceback.format_exception(type(exc), exc, exc.__traceback__)
        tb_str = "".join(tb)
        
        # Log the exception with full traceback
        logger.error(
            f"Unhandled exception: {type(exc).__name__}: {str(exc)} - "
            f"Request: {request.method} {request.url.path}\n{tb_str}"
        )
        
        # Prepare the error response
        error_detail = ErrorDetail(
            message="Internal server error" if not self.debug else str(exc),
            code="internal_server_error",
            details={
                "type": type(exc).__name__,
                "traceback": tb_str if self.debug else None
            } if self.debug else None,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            exception=exc,
            request_id=request_id
        )
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_detail.to_dict()
        )
    
    @staticmethod
    def format_error_response(
        message: str,
        code: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Format a standard error response
        
        Args:
            message: The error message
            code: The error code
            status_code: The HTTP status code
            details: Additional error details
            request_id: The request ID
            
        Returns:
            Dict: The formatted error response
        """
        error_detail = ErrorDetail(
            message=message,
            code=code,
            details=details,
            status_code=status_code,
            request_id=request_id
        )
        
        return error_detail.to_dict()