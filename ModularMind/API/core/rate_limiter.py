"""
Rate limiting implementation for API endpoints
"""
from typing import Dict, Optional, Callable, Tuple
import time
import asyncio
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import redis
from redis.exceptions import RedisError
import logging

logger = logging.getLogger(__name__)

class RedisRateLimiter:
    """Rate limiter implementation using Redis"""
    
    def __init__(
        self, 
        redis_url: str,
        default_limit: int = 100,  # requests per minute
        default_window: int = 60,  # window size in seconds
    ):
        self.redis_url = redis_url
        self.default_limit = default_limit
        self.default_window = default_window
        self._redis_client = None
    
    @property
    def redis_client(self) -> redis.Redis:
        """Lazy initialization of Redis client"""
        if self._redis_client is None:
            self._redis_client = redis.from_url(
                self.redis_url, 
                decode_responses=True,
                socket_connect_timeout=2.0,
                socket_timeout=2.0
            )
        return self._redis_client
    
    async def check_rate_limit(
        self, 
        key: str, 
        limit: Optional[int] = None, 
        window: Optional[int] = None
    ) -> Tuple[bool, Dict[str, int]]:
        """
        Check if the request is within rate limits
        
        Args:
            key: Unique identifier for the rate limit (e.g. IP address, API key)
            limit: Maximum number of requests allowed in the time window
            window: Time window in seconds
            
        Returns:
            Tuple containing:
            - Boolean indicating if the request is allowed
            - Dictionary with rate limit information (limit, remaining, reset)
        """
        limit = limit or self.default_limit
        window = window or self.default_window
        
        try:
            # Use Redis MULTI/EXEC to ensure atomicity
            pipe = self.redis_client.pipeline()
            
            # Current timestamp
            now = int(time.time())
            
            # Key for this rate limit window
            redis_key = f"ratelimit:{key}:{now // window}"
            
            # Increment counter and get new value
            count = pipe.incr(redis_key).execute()[0]
            
            # Set expiration if this is the first request in this window
            if count == 1:
                self.redis_client.expire(redis_key, window)
            
            # Calculate reset time
            reset = (now // window + 1) * window
            
            # Check if the request exceeds the limit
            remaining = max(0, limit - count)
            allowed = count <= limit
            
            return allowed, {
                "limit": limit,
                "remaining": remaining,
                "reset": reset
            }
            
        except RedisError as e:
            logger.error(f"Redis error in rate limiter: {str(e)}")
            # In case of Redis failure, allow the request but log the error
            return True, {
                "limit": limit,
                "remaining": 1,
                "reset": int(time.time()) + window
            }


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for rate limiting API requests"""
    
    def __init__(
        self, 
        app,
        redis_url: str,
        default_limit: int = 100,
        default_window: int = 60,
        get_key: Optional[Callable[[Request], str]] = None,
        excluded_paths: Optional[list] = None
    ):
        super().__init__(app)
        self.rate_limiter = RedisRateLimiter(
            redis_url=redis_url,
            default_limit=default_limit,
            default_window=default_window
        )
        self.get_key = get_key or self._default_get_key
        self.excluded_paths = excluded_paths or ["/health", "/metrics"]
    
    def _default_get_key(self, request: Request) -> str:
        """
        Default function to get the rate limit key from a request.
        Uses the client IP address or API key if available.
        """
        # Check for API key in authorization header
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            return f"apikey:{auth[7:]}"
        
        # Fall back to client IP
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # In case of multiple proxies, get the original client IP
            return f"ip:{forwarded.split(',')[0].strip()}"
        
        return f"ip:{request.client.host}"
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request, apply rate limiting, and pass to the next middleware"""
        # Skip rate limiting for excluded paths
        if request.url.path in self.excluded_paths:
            return await call_next(request)
        
        # Get rate limit key for this request
        key = self.get_key(request)
        
        # Check rate limit
        allowed, info = await self.rate_limiter.check_rate_limit(key)
        
        # Add rate limit headers to all responses
        response = await call_next(request) if allowed else JSONResponse(
            status_code=429,
            content={
                "error": {
                    "message": "Rate limit exceeded",
                    "code": "rate_limit_exceeded"
                }
            }
        )
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(info["reset"])
        
        if not allowed:
            response.headers["Retry-After"] = str(info["reset"] - int(time.time()))
        
        return response