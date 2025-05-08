from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time
import redis
from app.core.settings import get_settings

settings = get_settings()

class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=0,
            decode_responses=True
        )
        self.rate_limit = settings.RATE_LIMIT_PER_MINUTE
        self.window = 60  # 1 minute window
        
    async def dispatch(self, request: Request, call_next) -> Response:
        client_ip = request.client.host
        
        # Skip rate limiting for whitelisted IPs
        if client_ip in settings.RATE_LIMIT_WHITELIST:
            return await call_next(request)
            
        current = int(time.time())
        key = f"rate_limit:{client_ip}:{current // self.window}"
        
        # Increment counter for this window
        requests = self.redis_client.incr(key)
        
        # Set expiry if this is the first request in the window
        if requests == 1:
            self.redis_client.expire(key, self.window)
            
        if requests > self.rate_limit:
            return Response(
                content="Rate limit exceeded",
                status_code=429,
                headers={
                    "Retry-After": str(self.window - (current % self.window))
                }
            )
            
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(self.rate_limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, self.rate_limit - requests))
        response.headers["X-RateLimit-Reset"] = str(self.window - (current % self.window))
        
        return response