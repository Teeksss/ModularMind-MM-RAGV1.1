from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordRequestForm
from typing import Dict, Any, Optional
import jwt
from datetime import datetime, timedelta
import uuid

from app.models.user import (
    User, 
    UserCreate, 
    UserResponse, 
    Token, 
    TokenData,
    RefreshTokenRequest
)
from app.api.deps import (
    authenticate_user, 
    create_access_token, 
    create_refresh_token,
    get_current_user,
    update_user_last_login
)
from app.db.session import get_db
from app.core.settings import get_settings
from app.utils.password import get_password_hash

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse)
async def register_user(user_create: UserCreate):
    """
    Register a new user.
    
    - **username**: Username (must be unique)
    - **email**: Email address (must be unique)
    - **password**: Password (will be hashed)
    - **full_name**: User's full name
    """
    # Check if username already exists
    async with get_db() as db:
        existing_username = await db.fetch_one(
            "SELECT id FROM users WHERE username = $1", user_create.username
        )
        
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        
        # Check if email already exists
        existing_email = await db.fetch_one(
            "SELECT id FROM users WHERE email = $1", user_create.email
        )
        
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Create the user
        user_id = str(uuid.uuid4())
        hashed_password = get_password_hash(user_create.password)
        
        query = """
        INSERT INTO users (
            id, username, email, full_name, hashed_password, is_active, role, 
            created_at, preferences
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        RETURNING id, username, email, full_name, is_active, role, created_at, preferences
        """
        
        values = (
            user_id,
            user_create.username,
            user_create.email,
            user_create.full_name,
            hashed_password,
            True,  # is_active
            "user",  # role
            datetime.utcnow(),
            {"theme": "system", "language": "tr", "notification_enabled": True, "items_per_page": 10}  # default preferences
        )
        
        result = await db.fetch_one(query, *values)
        
        return UserResponse(**result)


@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Get an access token using username and password.
    
    Uses OAuth2 password flow.
    """
    user = await authenticate_user(form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.security.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username, "token_type": "access"},
        expires_delta=access_token_expires
    )
    
    # Create refresh token
    refresh_token = create_refresh_token(
        data={"sub": user.username}
    )
    
    # Update last login
    await update_user_last_login(user.id)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user,
    }


@router.post("/login", response_model=Token)
async def login(
    username: str = Body(...),
    password: str = Body(...),
    remember_me: bool = Body(False)
):
    """
    Login with username/email and password.
    
    - **username**: Username or email
    - **password**: Password
    - **remember_me**: Whether to use extended token expiry
    """
    user = await authenticate_user(username, password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    # Token expiry depends on remember_me
    if remember_me:
        access_token_expires = timedelta(days=7)  # Extended expiry
    else:
        access_token_expires = timedelta(minutes=settings.security.access_token_expire_minutes)
    
    # Create access token
    access_token = create_access_token(
        data={"sub": user.username, "token_type": "access"},
        expires_delta=access_token_expires
    )
    
    # Create refresh token
    refresh_token = create_refresh_token(
        data={"sub": user.username}
    )
    
    # Update last login
    await update_user_last_login(user.id)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user,
    }


@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_request: RefreshTokenRequest):
    """
    Refresh an access token using a refresh token.
    
    - **refresh_token**: A valid refresh token
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode and validate refresh token
        payload = jwt.decode(
            refresh_request.refresh_token, 
            settings.security.secret_key, 
            algorithms=["HS256"]
        )
        
        username: str = payload.get("sub")
        token_type: str = payload.get("token_type", "refresh")
        
        if username is None or token_type != "refresh":
            raise credentials_exception
        
        # Get user
        async with get_db() as db:
            query = """
            SELECT id, username, email, full_name, is_active, role, created_at, 
                   last_login, preferences
            FROM users
            WHERE username = $1
            """
            result = await db.fetch_one(query, username)
            
            if not result:
                raise credentials_exception
            
            user = User(**result)
            
            if not user.is_active:
                raise HTTPException(status_code=400, detail="Inactive user")
        
        # Create new access token
        access_token_expires = timedelta(minutes=settings.security.access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": user.username, "token_type": "access"},
            expires_delta=access_token_expires
        )
        
        # Create new refresh token
        new_refresh_token = create_refresh_token(
            data={"sub": user.username}
        )
        
        return {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "user": user,
        }
    
    except jwt.PyJWTError:
        raise credentials_exception


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return current_user


@router.post("/logout")
async def logout():
    """
    Logout current user.
    
    Note: The actual token invalidation happens client-side.
    This endpoint exists for logging and future server-side invalidation.
    """
    return {"detail": "Successfully logged out"}