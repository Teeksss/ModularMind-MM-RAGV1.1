from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm.exc import NoResultFound
from pydantic import ValidationError
import logging
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class ErrorResponse:
    """Standardized error response model."""
    
    @staticmethod
    def create(
        status_code: int, 
        message: str, 
        detail: Optional[Union[str, List[Dict[str, Any]]]] = None,
        error_code: Optional[str] = None
    ) -> JSONResponse:
        """Create an error response with consistent format."""
        content = {
            "status": "error",
            "message": message,
        }
        
        if detail:
            content["detail"] = detail
            
        if error_code:
            content["error_code"] = error_code
            
        return JSONResponse(
            status_code=status_code,
            content=content
        )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors."""
    # Log the error
    logger.warning(f"Validation error: {exc}")
    
    # Format errors for response
    errors = []
    for error in exc.errors():
        errors.append({
            "loc": error["loc"],
            "msg": error["msg"],
            "type": error["type"]
        })
    
    return ErrorResponse.create(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        message="Validation error",
        detail=errors,
        error_code="VALIDATION_ERROR"
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """Handle SQLAlchemy errors."""
    # Log the error
    logger.error(f"Database error: {str(exc)}", exc_info=True)
    
    return ErrorResponse.create(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message="Database error",
        detail=str(exc),
        error_code="DATABASE_ERROR"
    )


async def not_found_exception_handler(request: Request, exc: NoResultFound):
    """Handle not found errors."""
    return ErrorResponse.create(
        status_code=status.HTTP_404_NOT_FOUND,
        message="Resource not found",
        error_code="NOT_FOUND"
    )


async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    # Log the error
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    
    return ErrorResponse.create(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message="An unexpected error occurred",
        detail=str(exc),
        error_code="SERVER_ERROR"
    )


async def pydantic_validation_exception_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors."""
    # Log the error
    logger.warning(f"Pydantic validation error: {exc}")
    
    # Format errors for response
    errors = []
    for error in exc.errors():
        errors.append({
            "loc": error["loc"],
            "msg": error["msg"],
            "type": error["type"]
        })
    
    return ErrorResponse.create(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        message="Data validation error",
        detail=errors,
        error_code="VALIDATION_ERROR"
    )


def register_exception_handlers(app):
    """Register all exception handlers with the FastAPI app."""
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    app.add_exception_handler(NoResultFound, not_found_exception_handler)
    app.add_exception_handler(ValidationError, pydantic_validation_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)