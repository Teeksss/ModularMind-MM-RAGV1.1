from datetime import timedelta
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from ModularMind.API.core.auth import (
    create_access_token,
    get_current_active_user,
    jwt_settings
)
from ModularMind.API.models.user import User, UserCreate
from ModularMind.API.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["authentication"])

class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user: Dict[str, Any]

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    user: Dict[str, Any]

class RegisterResponse(BaseModel):
    message: str
    user_id: str

@router.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Token:
    """
    Kullanıcı adı ve şifre ile JWT token alır.
    """
    user_service = UserService()
    user = user_service.get_by_username(form_data.username)
    
    if not user or not user.verify_password(form_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz kullanıcı adı veya şifre",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Kullanıcı aktif mi kontrol et
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kullanıcı hesabı aktif değil",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Son giriş zamanını güncelle
    user_service.update_login_time(user.id)
    
    # Token oluştur
    access_token_expires = timedelta(minutes=jwt_settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username, "email": user.email, "role": user.role},
        expires_delta=access_token_expires
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=jwt_settings.access_token_expire_minutes * 60,
        user=user.to_response()
    )

@router.post("/login", response_model=LoginResponse)
async def login(
    username: str,
    password: str
) -> LoginResponse:
    """
    Kullanıcı adı ve şifre ile giriş yapar.
    """
    user_service = UserService()
    user = user_service.get_by_username(username)
    
    if not user or not user.verify_password(password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz kullanıcı adı veya şifre",
        )
    
    # Kullanıcı aktif mi kontrol et
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kullanıcı hesabı aktif değil",
        )
    
    # Son giriş zamanını güncelle
    user_service.update_login_time(user.id)
    
    # Token oluştur
    access_token_expires = timedelta(minutes=jwt_settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username, "email": user.email, "role": user.role},
        expires_delta=access_token_expires
    )
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=jwt_settings.access_token_expire_minutes * 60,
        user=user.to_response()
    )

@router.post("/register", response_model=RegisterResponse)
async def register(
    user_create: UserCreate
) -> RegisterResponse:
    """
    Yeni kullanıcı kaydı oluşturur.
    """
    user_service = UserService()
    
    # Kullanıcı adı veya e-posta zaten kullanımda mı kontrol et
    if user_service.get_by_username(user_create.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu kullanıcı adı zaten kullanımda",
        )
    
    if user_service.get_by_email(user_create.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu e-posta adresi zaten kullanımda",
        )
    
    # Kullanıcıyı oluştur
    user = user_service.create(user_create)
    
    return RegisterResponse(
        message="Kullanıcı başarıyla oluşturuldu",
        user_id=user.id
    )

@router.get("/me", response_model=Dict[str, Any])
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """
    Mevcut kullanıcının bilgilerini döndürür.
    """
    return current_user.to_response()

@router.post("/logout")
async def logout() -> Dict[str, str]:
    """
    Kullanıcı çıkışı yapar.
    Not: JWT tabanlı sistemlerde client tarafında token'ın kaldırılması yeterlidir.
    Bu endpoint yalnızca başarılı bir yanıt döndürür.
    """
    return {"message": "Başarıyla çıkış yapıldı"}