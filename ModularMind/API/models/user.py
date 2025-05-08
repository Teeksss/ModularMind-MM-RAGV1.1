from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field, root_validator, validator
from enum import Enum
import uuid
import re
import bcrypt

class UserRole(str, Enum):
    """Kullanıcı rolleri."""
    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"
    GUEST = "guest"

class UserStatus(str, Enum):
    """Kullanıcı durumları."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    SUSPENDED = "suspended"

class UserCreate(BaseModel):
    """Yeni kullanıcı oluşturma modeli."""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None
    role: UserRole = UserRole.USER
    
    @validator('username')
    def username_alphanumeric(cls, v):
        """Username sadece alfanumerik karakterler ve alt çizgi içerebilir."""
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('Username sadece harf, rakam ve alt çizgi içerebilir')
        return v
    
    @validator('password')
    def password_strength(cls, v):
        """Şifre gücünü kontrol eder."""
        if not any(c.isupper() for c in v):
            raise ValueError('Şifre en az bir büyük harf içermelidir')
        if not any(c.islower() for c in v):
            raise ValueError('Şifre en az bir küçük harf içermelidir')
        if not any(c.isdigit() for c in v):
            raise ValueError('Şifre en az bir rakam içermelidir')
        return v

class UserUpdate(BaseModel):
    """Kullanıcı güncelleme modeli."""
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8)
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None
    
    @validator('password')
    def password_strength(cls, v):
        """Şifre gücünü kontrol eder."""
        if v is None:
            return v
        if not any(c.isupper() for c in v):
            raise ValueError('Şifre en az bir büyük harf içermelidir')
        if not any(c.islower() for c in v):
            raise ValueError('Şifre en az bir küçük harf içermelidir')
        if not any(c.isdigit() for c in v):
            raise ValueError('Şifre en az bir rakam içermelidir')
        return v

class User(BaseModel):
    """Kullanıcı modeli."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    role: UserRole = UserRole.USER
    status: UserStatus = UserStatus.ACTIVE
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    settings: Dict[str, Any] = Field(default_factory=dict)
    permissions: List[str] = Field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """Dict'ten User oluşturur."""
        return cls(**data)
    
    def to_dict(self) -> Dict[str, Any]:
        """User'ı Dict'e dönüştürür."""
        return self.dict(by_alias=True)
    
    def to_response(self) -> Dict[str, Any]:
        """API yanıtı için güvenli bir Dict döndürür."""
        data = self.dict(exclude={"hashed_password"})
        return data
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Şifreyi hashler."""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode(), salt)
        return hashed.decode()
    
    def verify_password(self, password: str) -> bool:
        """Şifreyi doğrular."""
        return bcrypt.checkpw(password.encode(), self.hashed_password.encode())
    
    def has_permission(self, permission: str) -> bool:
        """Kullanıcının belirli bir yetkiye sahip olup olmadığını kontrol eder."""
        if self.role == UserRole.ADMIN:
            return True
        return permission in self.permissions