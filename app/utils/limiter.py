import asyncio
import time
import functools
from fastapi import HTTPException, Request
from typing import Dict, Set, Optional, Callable, Any

from app.core.config import settings

# In-memory storage for rate limiting
# In a production environment, this should be replaced with Redis or another distributed store
class RateLimiter:
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, Dict[float, int]] = {}
    
    def is_rate_limited(self, key: str) -> bool:
        """Check if a key is rate limited."""
        now = time.time()
        
        # Initialize if key doesn't exist
        if key not in self.requests:
            self.requests[key] = {}
        
        # Clean up old requests
        self._cleanup(key, now)
        
        # Count requests in current window
        total_requests = sum(self.requests[key].values())
        
        # Check if rate limited
        return total_requests >= self.max_requests
    
    def add_request(self, key: str, count: int = 1) -> None:
        """Add a request for a key."""
        now = time.time()
        
        # Initialize if key doesn't exist
        if key not in self.requests:
            self.requests[key] = {}
        
        # Add request
        self.requests[key][now] = count
        
        # Clean up old requests
        self._cleanup(key, now)
    
    def _cleanup(self, key: str, now: float) -> None:
        """Remove requests outside the window."""
        cutoff = now - self.window_seconds
        self.requests[key] = {
            ts: count for ts, count in self.requests[key].items()
            if ts >= cutoff
        }


# Concurrency limiter using semaphore
class ConcurrencyLimiter:
    def __init__(self, max_concurrent: int = 10):
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def acquire(self) -> bool:
        """Acquire the semaphore."""
        return await self.semaphore.acquire()
    
    def release(self) -> None:
        """Release the semaphore."""
        self.semaphore.release()


# Create instances
rate_limiter_instance = RateLimiter(
    max_requests=settings.max_concurrent_requests * 10,
    window_seconds=60
)

concurrency_limiter_instance = ConcurrencyLimiter(
    max_concurrent=settings.max_concurrent_requests
)


# Rate limiting decorator
def rate_limiter(func):
    """Decorator to apply rate limiting to a route."""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Get client IP or identifier (simplified)
        client_id = "default_client"  # In a real app, extract from request
        
        # Check rate limit
        if rate_limiter_instance.is_rate_limited(client_id):
            raise HTTPException(
                status_code=429,
                detail="Too many requests"
            )
        
        # Add request to limiter
        rate_limiter_instance.add_request(client_id)
        
        # Execute the original function
        return await func(*args, **kwargs)
    
    return wrapper


# Concurrency limiting decorator
def concurrency_limiter(func):
    """Decorator to apply concurrency limiting to a route."""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Acquire semaphore
        await concurrency_limiter_instance.acquire()
        
        try:
            # Execute the original function
            return await func(*args, **kwargs)
        finally:
            # Release semaphore
            concurrency_limiter_instance.release()
    
    return wrapper