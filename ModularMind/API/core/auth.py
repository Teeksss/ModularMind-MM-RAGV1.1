"""
Authentication and authorization utilities
"""
from typing import Optional, List, Dict, Any
import time
from datetime import datetime, timedelta
from pydantic import BaseModel
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from ModularMind.API.models.user import User
from ModularMind.API.models.api_token import APIToken
from ModularMind.API.db.session import get_db
from ModularMind.API.config import Config

# JWT settings
JWT_SECRET = Config.get("JWT_SECRET", "your-secret-key-for-jwt")
JWT_ALGORITHM = Config.get("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_DELTA = Config.get("JWT_EXPIRATION_DELTA", 60 * 24)  # 1 day in minutes

# Security bearer token scheme
security = HTTPBearer()

class JWTPayload(BaseModel):
    """JWT token payload model"""
    sub: str  # user ID
    exp: int  # expiration timestamp
    iat: int  # issued at timestamp
    role: str  # user role
    type: str  # token type (access, refresh, api)


def create_jwt_token(user_id: str, role: str, token_type: str = "access", expires_minutes: Optional[int] = None) -> str:
    """Create a JWT token for a user"""
    expires_delta = expires_minutes or JWT_EXPIRATION_DELTA
    expire = datetime.utcnow() + timedelta(minutes=expires_delta)
    
    payload = {
        "sub": user_id,
        "exp": expire.timestamp(),
        "iat": time.time(),
        "role": role,
        "type": token_type
    }
    
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_jwt_token(token: str) -> Optional[JWTPayload]:
    """Decode and validate a JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return JWTPayload(**payload)
    except jwt.PyJWTError:
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Dependency to get the current user from the JWT token"""
    token = credentials.credentials
    
    # Decode and validate token
    payload = decode_jwt_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check token type
    if payload.type not in ["access", "api"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user from database
    user = db.query(User).filter(User.id == payload.sub).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # For API tokens, update last used timestamp
    if payload.type == "api":
        api_token = db.query(APIToken).filter(
            APIToken.user_id == user.id,
            APIToken.token_hash == token
        ).first()
        
        if api_token:
            api_token.last_used_at = datetime.utcnow()
            db.commit()
    
    return user


def require_roles(allowed_roles: List[str]):
    """Dependency factory for role-based access control"""
    
    async def role_checker(user: User = Depends(get_current_user)) -> User:
        """Check if the user has one of the allowed roles"""
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user
    
    return role_checker


# Commonly used role dependencies
require_admin = require_roles(["admin"])
require_admin_or_editor = require_roles(["admin", "editor"])