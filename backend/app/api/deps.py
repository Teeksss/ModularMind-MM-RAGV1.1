from typing import Optional, Union, Dict, Any
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status, Header, Cookie, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
import uuid

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.token import TokenPayload

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.api_prefix}/auth/login",
    auto_error=False  # Don't auto-error to allow checking cookies
)

# JWT Configuration
SECRET_KEY = settings.jwt_secret_key
ALGORITHM = settings.jwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes
REFRESH_TOKEN_EXPIRE_DAYS = settings.refresh_token_expire_days


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a new access token with expiration time."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "type": "access"})
    
    # Add jti (JWT ID) for token tracking/revocation
    to_encode.update({"jti": str(uuid.uuid4())})
    
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create a new refresh token with expiration time."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({"exp": expire, "type": "refresh"})
    
    # Add jti (JWT ID) for token tracking/revocation
    to_encode.update({"jti": str(uuid.uuid4())})
    
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_token_from_request(
    req: Request,
    token: Optional[str] = Depends(oauth2_scheme),
) -> Optional[str]:
    """
    Extract token from various sources in the request.
    
    Priority:
    1. Authorization header
    2. Cookie
    3. Query parameter
    """
    # Already extracted from Authorization header by oauth2_scheme
    if token:
        return token
    
    # Check cookies
    token = req.cookies.get("access_token")
    if token:
        return token
    
    # Check query parameters as last resort
    token = req.query_params.get("access_token")
    if token:
        return token
    
    return None


async def get_current_user(
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(get_token_from_request)
) -> Optional[User]:
    """
    Validate access token and return current user.
    
    Raises HTTPException if authentication fails.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not token:
        raise credentials_exception
    
    try:
        # Decode JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Extract user info
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        # Validate token contents
        if user_id is None:
            raise credentials_exception
            
        if token_type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type. Please use access token.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        token_data = TokenPayload(**payload)
        
        # Check token expiration
        if datetime.fromtimestamp(token_data.exp) < datetime.now():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
    except JWTError:
        raise credentials_exception
    
    # Get user from database
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
        
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
        )
        
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user. Just a convenience wrapper."""
    return current_user


async def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Check if current user is an admin."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )
        
    return current_user


# Optional current user (doesn't raise exception if not authenticated)
async def get_optional_user(
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(get_token_from_request)
) -> Optional[User]:
    """Get current user without raising exception if not authenticated."""
    if not token:
        return None
    
    try:
        # Decode JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Extract user info
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        # Validate token contents
        if user_id is None or token_type != "access":
            return None
        
        token_data = TokenPayload(**payload)
        
        # Check token expiration
        if datetime.fromtimestamp(token_data.exp) < datetime.now():
            return None
            
    except JWTError:
        return None
    
    # Get user from database
    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active:
        return None
        
    return user