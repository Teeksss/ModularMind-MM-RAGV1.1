"""
Error handling utilities for the API
"""
from typing import Any, Dict, List, Optional, Union
import logging
import traceback
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

logger = logging.getLogger(__name__)

class APIError(Exception):
    """Base API error class"""
    def __init__(
        self, 
        message: str, 
        status_code: int = 500, 
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.code = code or self._get_default_code()
        self.details = details
        super().__init__(self.message)
    
    def _get_default_code(self) -> str:
        """Get default error code based on class name"""
        class_name = self.__class__.__name__
        if class_name == "APIError":
            return "internal_error"
        # Convert CamelCase to snake_case and remove "Error" suffix
        import re
        name = re.sub(r'(?<!^)(?=[A-Z])', '_', class_name).lower()
        if name.endswith("_error"):
            name = name[:-6]
        return name

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary"""
        response = {
            "error": {
                "message": self.message,
                "code": self.code
            }
        }
        if self.details:
            response["error"]["details"] = self.details
        return response


class NotFoundError(APIError):
    """Resource not found error"""
    def __init__(
        self, 
        message: str = "Resource not found", 
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, status.HTTP_404_NOT_FOUND, code, details)


class ValidationAPIError(APIError):
    """Validation error for API requests"""
    def __init__(
        self, 
        message: str = "Validation error", 
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, status.HTTP_422_UNPROCESSABLE_ENTITY, code, details)


class AuthenticationError(APIError):
    """Authentication error"""
    def __init__(
        self, 
        message: str = "Authentication failed", 
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, status.HTTP_401_UNAUTHORIZED, code, details)


class AuthorizationError(APIError):
    """Authorization error"""
    def __init__(
        self, 
        message: str = "You don't have permission to perform this action", 
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, status.HTTP_403_FORBIDDEN, code, details)


class BadRequestError(APIError):
    """Bad request error"""
    def __init__(
        self, 
        message: str = "Bad request", 
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, status.HTTP_400_BAD_REQUEST, code, details)


class DatabaseError(APIError):
    """Database error"""
    def __init__(
        self, 
        message: str = "Database error", 
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, status.HTTP_500_INTERNAL_SERVER_ERROR, code, details)


class RateLimitError(APIError):
    """Rate limit exceeded error"""
    def __init__(
        self, 
        message: str = "Rate limit exceeded", 
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, status.HTTP_429_TOO_MANY_REQUESTS, code, details)


class ServiceUnavailableError(APIError):
    """Service unavailable error"""
    def __init__(
        self, 
        message: str = "Service temporarily unavailable", 
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, status.HTTP_503_SERVICE_UNAVAILABLE, code, details)


class ExternalServiceError(APIError):
    """External service error"""
    def __init__(
        self, 
        message: str = "External service error", 
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, status.HTTP_502_BAD_GATEWAY, code, details)


def setup_exception_handlers(app: FastAPI) -> None:
    """Setup exception handlers for the FastAPI application"""
    
    @app.exception_handler(APIError)
    async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
        """Handle API errors"""
        logger.error(f"API error: {exc.message}")
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict()
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        """Handle request validation errors"""
        error_details = []
        for error in exc.errors():
            error_details.append({
                "location": error["loc"],
                "message": error["msg"],
                "type": error["type"]
            })
        
        logger.warning(f"Validation error: {error_details}")
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "message": "Request validation error",
                    "code": "validation_error",
                    "details": {
                        "errors": error_details
                    }
                }
            }
        )
    
    @app.exception_handler(ValidationError)
    async def pydantic_validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
        """Handle Pydantic validation errors"""
        error_details = []
        for error in exc.errors():
            error_details.append({
                "location": error["loc"],
                "message": error["msg"],
                "type": error["type"]
            })
        
        logger.warning(f"Pydantic validation error: {error_details}")
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "message": "Data validation error",
                    "code": "validation_error",
                    "details": {
                        "errors": error_details
                    }
                }
            }
        )
    
    @app.exception_handler(SQLAlchemyError)
    async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        """Handle SQLAlchemy errors"""
        error_msg = str(exc)
        
        if isinstance(exc, IntegrityError):
            # Handle integrity errors (e.g., unique constraint violations)
            logger.warning(f"Database integrity error: {error_msg}")
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "error": {
                        "message": "Database constraint violation",
                        "code": "integrity_error",
                        "details": {
                            "error": error_msg
                        }
                    }
                }
            )
        
        # Log the full exception for other database errors
        logger.error(f"Database error: {error_msg}")
        logger.debug(traceback.format_exc())
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "message": "Database error occurred",
                    "code": "database_error"
                }
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle all other exceptions"""
        # Log the full exception
        logger.error(f"Unhandled exception: {str(exc)}")
        logger.error(traceback.format_exc())
        
        # In production, don't return the actual error message to avoid leaking sensitive info
        is_debug = app.debug
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "message": str(exc) if is_debug else "An unexpected error occurred",
                    "code": "internal_server_error",
                    "details": {
                        "type": exc.__class__.__name__
                    } if is_debug else None
                }
            }
        )