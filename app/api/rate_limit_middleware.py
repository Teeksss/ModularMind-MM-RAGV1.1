from fastapi import FastAPI, Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import time
import asyncio
from typing import Dict, List, Tuple, Callable, Optional, Any, Union
import logging
import redis.asyncio as redis
from redis.exceptions import RedisError
from datetime import datetime

from app.core.config import settings
from app.api.deps import get_current_user_optional
from app.utils.monitoring import log_rate_limit_hit

logger = logging.getLogger(__name__)

class RateLimitConfig:
    """Configuration for rate limiting."""
    
    def __init__(
        self,
        limit: int,
        window: int,
        key_func: Optional[Callable[[Request], str]] = None,
        exempt_when: Optional[Callable[[Request], bool]] = None
    ):
        """
        Initialize rate limit configuration.
        
        Args:
            limit: Maximum number of requests allowed in the time window
            window: Time window in seconds
            key_func: Function to generate a unique key for the request
            exempt_when: Function to determine if a request is exempt from rate limiting
        """
        self.limit = limit
        self.window = window
        self.key_func = key_func
        self.exempt_when = exempt_when


class RateLimitStore:
    """Store for rate limit data."""
    
    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize the rate limit store.
        
        Args:
            redis_url: Redis connection URL for distributed rate limiting
        """
        self.redis_url = redis_url
        self.redis_client = None
        self.local_store: Dict[str, List[float]] = {}
        self.use_redis = redis_url is not None
    
    async def setup(self):
        """Set up the rate limit store."""
        if self.use_redis:
            try:
                self.redis_client = redis.from_url(self.redis_url)
                await self.redis_client.ping()
                logger.info("Connected to Redis for rate limiting")
            except RedisError as e:
                logger.error(f"Failed to connect to Redis: {str(e)}")
                self.use_redis = False
                logger.warning("Falling back to local rate limiting")
    
    async def increment(self, key: str, window: int) -> Tuple[int, int]:
        """
        Increment the request count for a key.
        
        Args:
            key: The rate limit key
            window: The time window in seconds
            
        Returns:
            Tuple of (current_count, limit_reset_time)
        """
        now = time.time()
        
        if self.use_redis and self.redis_client:
            try:
                # Using Redis for distributed rate limiting
                redis_key = f"ratelimit:{key}"
                
                # Use pipeline to ensure atomic operations
                async with self.redis_client.pipeline() as pipe:
                    # Get current time
                    expiry_time = int(now) + window
                    
                    # Add the current timestamp to the sorted set
                    await pipe.zadd(redis_key, {str(now): now})
                    
                    # Remove timestamps outside the window
                    await pipe.zremrangebyscore(redis_key, 0, now - window)
                    
                    # Count the remaining timestamps in the window
                    await pipe.zcard(redis_key)
                    
                    # Set the expiry on the key to auto-cleanup
                    await pipe.expireat(redis_key, expiry_time)
                    
                    # Execute pipeline
                    _, _, count, _ = await pipe.execute()
                
                return count, expiry_time
            
            except RedisError as e:
                logger.error(f"Redis error in rate limiting: {str(e)}")
                # Fall back to local implementation
                return self._increment_local(key, window)
        else:
            # Use local implementation
            return self._increment_local(key, window)
    
    def _increment_local(self, key: str, window: int) -> Tuple[int, int]:
        """Local implementation of increment using in-memory storage."""
        now = time.time()
        
        # Initialize if key doesn't exist
        if key not in self.local_store:
            self.local_store[key] = []
        
        # Add current timestamp
        self.local_store[key].append(now)
        
        # Remove old timestamps
        self.local_store[key] = [t for t in self.local_store[key] if t > now - window]
        
        # Calculate reset time
        reset_time = int(now) + window
        
        return len(self.local_store[key]), reset_time
    
    async def close(self):
        """Close connections."""
        if self.use_redis and self.redis_client:
            await self.redis_client.close()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for API rate limiting."""
    
    def __init__(
        self, 
        app: ASGIApp,
        global_rate_limit: RateLimitConfig,
        path_rate_limits: Dict[str, RateLimitConfig] = None,
        redis_url: Optional[str] = None,
        exclude_paths: List[str] = None
    ):
        """
        Initialize the rate limit middleware.
        
        Args:
            app: The ASGI application
            global_rate_limit: Global rate limit configuration
            path_rate_limits: Path-specific rate limit configurations
            redis_url: Redis connection URL for distributed rate limiting
            exclude_paths: Paths to exclude from rate limiting
        """
        super().__init__(app)
        self.global_rate_limit = global_rate_limit
        self.path_rate_limits = path_rate_limits or {}
        self.store = RateLimitStore(redis_url)
        self.exclude_paths = exclude_paths or ["/health", "/metrics", "/docs", "/redoc", "/openapi.json"]
    
    async def initialize(self):
        """Initialize the middleware."""
        await self.store.setup()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request through the middleware.
        
        Args:
            request: The incoming request
            call_next: The next middleware or route handler
            
        Returns:
            The response from the next handler
        """
        # Skip rate limiting for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        # Determine which rate limit config to use
        rate_limit = self.path_rate_limits.get(request.url.path, self.global_rate_limit)
        
        # Check if request is exempt from rate limiting
        if rate_limit.exempt_when and rate_limit.exempt_when(request):
            return await call_next(request)
        
        # Generate rate limit key
        key = await self._generate_key(request, rate_limit)
        
        # Increment and check rate limit
        count, reset_time = await self.store.increment(key, rate_limit.window)
        
        # Set rate limit headers
        headers = {
            "X-RateLimit-Limit": str(rate_limit.limit),
            "X-RateLimit-Remaining": str(max(0, rate_limit.limit - count)),
            "X-RateLimit-Reset": str(reset_time)
        }
        
        # Check if rate limit is exceeded
        if count > rate_limit.limit:
            # Log rate limit hit
            endpoint = request.url.path
            user_type = await self._get_user_type(request)
            log_rate_limit_hit(endpoint, user_type)
            
            # Return rate limit exceeded response
            retry_after = reset_time - int(time.time())
            headers["Retry-After"] = str(max(1, retry_after))
            
            return Response(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded. Try again later."},
                headers=headers
            )
        
        # Process the request
        response = await call_next(request)
        
        # Add rate limit headers to response
        for header_name, header_value in headers.items():
            response.headers[header_name] = header_value
        
        return response
    
    async def _generate_key(self, request: Request, rate_limit: RateLimitConfig) -> str:
        """
        Generate a unique key for rate limiting.
        
        Args:
            request: The request
            rate_limit: The rate limit configuration
            
        Returns:
            A unique key for rate limiting
        """
        if rate_limit.key_func:
            return rate_limit.key_func(request)
        
        # Default implementation: Use IP and path
        client_ip = request.client.host if request.client else "unknown"
        
        # Try to get user identity if authenticated
        user = None
        try:
            user = await get_current_user_optional(request)
        except:
            pass
        
        # Use user ID if available, otherwise IP
        user_id = str(user.id) if user else client_ip
        
        # Combine with path
        return f"{user_id}:{request.url.path}"
    
    async def _get_user_type(self, request: Request) -> str:
        """
        Get the user type for logging.
        
        Args:
            request: The request
            
        Returns:
            The user type (authenticated, anonymous, or admin)
        """
        try:
            user = await get_current_user_optional(request)
            if user:
                return "admin" if user.is_admin else "authenticated"
            return "anonymous"
        except:
            return "anonymous"


def setup_rate_limiting(app: FastAPI):
    """
    Set up rate limiting for the application.
    
    Args:
        app: The FastAPI application
    """
    # Configure global rate limit (100 requests per minute for regular users)
    global_limit = RateLimitConfig(
        limit=100,
        window=60,
        exempt_when=lambda request: False
    )
    
    # Configure path-specific rate limits
    path_limits = {
        # Login/Authentication endpoints (10 requests per minute)
        "/api/v1/auth/login": RateLimitConfig(limit=10, window=60),
        "/api/v1/auth/token": RateLimitConfig(limit=10, window=60),
        
        # Document uploads (30 per hour)
        "/api/v1/documents": RateLimitConfig(limit=30, window=3600),
        
        # Chat endpoints (30 per minute)
        "/api/v1/chat/sessions": RateLimitConfig(limit=30, window=60),
        
        # Embedding endpoints (50 per minute)
        "/api/v1/embeddings": RateLimitConfig(limit=50, window=60),
        
        # Multimodal endpoints (30 per minute)
        "/api/v1/multimodal": RateLimitConfig(limit=30, window=60),
    }
    
    # Function to exempt admin users from rate limiting
    def is_admin_user(request: Request) -> bool:
        """Check if the user is an admin."""
        # This will be implemented in the actual application
        # based on the authentication system
        return False
    
    # Create rate limit middleware
    middleware = RateLimitMiddleware(
        app=app,
        global_rate_limit=global_limit,
        path_rate_limits=path_limits,
        redis_url=settings.redis_url,
        exclude_paths=["/health", "/metrics", "/docs", "/redoc", "/openapi.json"]
    )
    
    # Initialize the middleware
    asyncio.create_task(middleware.initialize())
    
    # Add middleware to application
    app.add_middleware(
        BaseHTTPMiddleware,
        dispatch=middleware.dispatch
    )
    
    logger.info("Rate limiting middleware configured")