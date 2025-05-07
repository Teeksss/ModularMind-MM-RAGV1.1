from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
from typing import Any, Dict, List, Optional, Union, Callable

# Import custom exceptions
from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    DocumentNotFoundError,
    ModelNotFoundError,
    VectorStoreError,
    RateLimitError,
    TaskQueueError,
    InvalidRequestError,
    ServiceUnavailableError
)

# Get logger
logger = logging.getLogger(__name__)

class ErrorDetail:
    """Helper class for standardized error responses."""
    
    @staticmethod
    def validation_error(errors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Format validation error response."""
        return {
            "error_code": "validation_error",
            "message": "Validation error",
            "details": errors
        }
    
    @staticmethod
    def authentication_error(message: str = "Authentication failed") -> Dict[str, Any]:
        """Format authentication error response."""
        return {
            "error_code": "authentication_error",
            "message": message
        }
    
    @staticmethod
    def authorization_error(message: str = "Not authorized to perform this action") -> Dict[str, Any]:
        """Format authorization error response."""
        return {
            "error_code": "authorization_error",
            "message": message
        }
    
    @staticmethod
    def not_found_error(message: str = "Resource not found") -> Dict[str, Any]:
        """Format not found error response."""
        return {
            "error_code": "not_found",
            "message": message
        }
    
    @staticmethod
    def rate_limit_error(message: str = "Rate limit exceeded") -> Dict[str, Any]:
        """Format rate limit error response."""
        return {
            "error_code": "rate_limit_exceeded",
            "message": message
        }
    
    @staticmethod
    def service_unavailable_error(message: str = "Service temporarily unavailable") -> Dict[str, Any]:
        """Format service unavailable error response."""
        return {
            "error_code": "service_unavailable",
            "message": message
        }
    
    @staticmethod
    def internal_server_error(message: str = "Internal server error") -> Dict[str, Any]:
        """Format internal server error response."""
        return {
            "error_code": "internal_server_error",
            "message": message
        }
    
    @staticmethod
    def bad_request_error(message: str = "Bad request") -> Dict[str, Any]:
        """Format bad request error response."""
        return {
            "error_code": "bad_request",
            "message": message
        }


def setup_error_handlers(app: FastAPI) -> None:
    """Set up global exception handlers for the application."""
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        """Handle validation errors."""
        errors = []
        for error in exc.errors():
            error_detail = {
                "loc": error["loc"],
                "msg": error["msg"],
                "type": error["type"]
            }
            errors.append(error_detail)
            
        logger.warning(f"Validation error: {errors}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=ErrorDetail.validation_error(errors)
        )
    
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        """Handle HTTP exceptions."""
        logger.warning(f"HTTP error {exc.status_code}: {exc.detail}")
        
        if exc.status_code == status.HTTP_404_NOT_FOUND:
            content = ErrorDetail.not_found_error(exc.detail)
        elif exc.status_code == status.HTTP_401_UNAUTHORIZED:
            content = ErrorDetail.authentication_error(exc.detail)
        elif exc.status_code == status.HTTP_403_FORBIDDEN:
            content = ErrorDetail.authorization_error(exc.detail)
        elif exc.status_code == status.HTTP_400_BAD_REQUEST:
            content = ErrorDetail.bad_request_error(exc.detail)
        elif exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            content = ErrorDetail.rate_limit_error(exc.detail)
        elif exc.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
            content = ErrorDetail.service_unavailable_error(exc.detail)
        else:
            content = {"message": exc.detail, "error_code": f"http_{exc.status_code}"}
        
        return JSONResponse(
            status_code=exc.status_code,
            content=content,
            headers=getattr(exc, "headers", None)
        )
    
    @app.exception_handler(AuthenticationError)
    async def authentication_exception_handler(request: Request, exc: AuthenticationError) -> JSONResponse:
        """Handle authentication errors."""
        logger.warning(f"Authentication error: {str(exc)}")
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=ErrorDetail.authentication_error(str(exc))
        )
    
    @app.exception_handler(AuthorizationError)
    async def authorization_exception_handler(request: Request, exc: AuthorizationError) -> JSONResponse:
        """Handle authorization errors."""
        logger.warning(f"Authorization error: {str(exc)}")
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=ErrorDetail.authorization_error(str(exc))
        )
    
    @app.exception_handler(DocumentNotFoundError)
    async def document_not_found_exception_handler(request: Request, exc: DocumentNotFoundError) -> JSONResponse:
        """Handle document not found errors."""
        logger.warning(f"Document not found: {str(exc)}")
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=ErrorDetail.not_found_error(str(exc))
        )
    
    @app.exception_handler(ModelNotFoundError)
    async def model_not_found_exception_handler(request: Request, exc: ModelNotFoundError) -> JSONResponse:
        """Handle model not found errors."""
        logger.warning(f"Model not found: {str(exc)}")
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=ErrorDetail.not_found_error(str(exc))
        )
    
    @app.exception_handler(VectorStoreError)
    async def vector_store_exception_handler(request: Request, exc: VectorStoreError) -> JSONResponse:
        """Handle vector store errors."""
        logger.error(f"Vector store error: {str(exc)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorDetail.internal_server_error(str(exc))
        )
    
    @app.exception_handler(RateLimitError)
    async def rate_limit_exception_handler(request: Request, exc: RateLimitError) -> JSONResponse:
        """Handle rate limit errors."""
        logger.warning(f"Rate limit exceeded: {str(exc)}")
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content=ErrorDetail.rate_limit_error(str(exc)),
            headers={"Retry-After": str(exc.retry_after) if hasattr(exc, "retry_after") else "60"}
        )
    
    @app.exception_handler(TaskQueueError)
    async def task_queue_exception_handler(request: Request, exc: TaskQueueError) -> JSONResponse:
        """Handle task queue errors."""
        logger.error(f"Task queue error: {str(exc)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorDetail.internal_server_error(str(exc))
        )
    
    @app.exception_handler(InvalidRequestError)
    async def invalid_request_exception_handler(request: Request, exc: InvalidRequestError) -> JSONResponse:
        """Handle invalid request errors."""
        logger.warning(f"Invalid request: {str(exc)}")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorDetail.bad_request_error(str(exc))
        )
    
    @app.exception_handler(ServiceUnavailableError)
    async def service_unavailable_exception_handler(request: Request, exc: ServiceUnavailableError) -> JSONResponse:
        """Handle service unavailable errors."""
        logger.error(f"Service unavailable: {str(exc)}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=ErrorDetail.service_unavailable_error(str(exc)),
            headers={"Retry-After": str(exc.retry_after) if hasattr(exc, "retry_after") else "60"}
        )
    
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle all other exceptions."""
        # Log the full exception for debugging
        logger.exception(f"Unhandled exception: {str(exc)}")
        
        # In production, don't expose internal error details to clients
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorDetail.internal_server_error("An unexpected error occurred. Please try again later.")
        )