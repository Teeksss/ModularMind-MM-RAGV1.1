class BaseApplicationError(Exception):
    """Base class for all application exceptions."""
    
    def __init__(self, message: str = None):
        self.message = message
        super().__init__(self.message)


class AuthenticationError(BaseApplicationError):
    """Authentication error."""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message)


class AuthorizationError(BaseApplicationError):
    """Authorization error."""
    
    def __init__(self, message: str = "Not authorized to perform this action"):
        super().__init__(message)


class DocumentNotFoundError(BaseApplicationError):
    """Document not found error."""
    
    def __init__(self, document_id: str = None):
        message = f"Document not found: {document_id}" if document_id else "Document not found"
        super().__init__(message)


class ModelNotFoundError(BaseApplicationError):
    """Model not found error."""
    
    def __init__(self, model_name: str = None):
        message = f"Model not found: {model_name}" if model_name else "Model not found"
        super().__init__(message)


class VectorStoreError(BaseApplicationError):
    """Vector store error."""
    
    def __init__(self, message: str = "Vector store operation failed"):
        super().__init__(message)


class RateLimitError(BaseApplicationError):
    """Rate limit error."""
    
    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = 60):
        self.retry_after = retry_after
        super().__init__(message)


class TaskQueueError(BaseApplicationError):
    """Task queue error."""
    
    def __init__(self, message: str = "Task queue operation failed"):
        super().__init__(message)


class InvalidRequestError(BaseApplicationError):
    """Invalid request error."""
    
    def __init__(self, message: str = "Invalid request"):
        super().__init__(message)


class ServiceUnavailableError(BaseApplicationError):
    """Service unavailable error."""
    
    def __init__(self, message: str = "Service temporarily unavailable", retry_after: int = 60):
        self.retry_after = retry_after
        super().__init__(message)


class StorageError(BaseApplicationError):
    """Storage error."""
    
    def __init__(self, message: str = "Storage operation failed"):
        super().__init__(message)


class FeedbackError(BaseApplicationError):
    """Feedback error."""
    
    def __init__(self, message: str = "Feedback operation failed"):
        super().__init__(message)


class FineTuningError(BaseApplicationError):
    """Fine-tuning error."""
    
    def __init__(self, message: str = "Fine-tuning operation failed"):
        super().__init__(message)