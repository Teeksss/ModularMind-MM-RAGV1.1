from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
from pymongo.errors import DuplicateKeyError
from fastapi import HTTPException, status

from ModularMind.API.db.base import DatabaseManager
from ModularMind.API.models.user import User, UserCreate, UserUpdate, UserRole, UserStatus
from ModularMind.API.core.cache import RedisCache, cached

logger = logging.getLogger(__name__)

class UserService:
    """Kullanıcı yönetimi servisi."""
    
    COLLECTION = "users"
    CACHE_PREFIX = "user:"
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.collection = self.db_manager.get_collection(self.COLLECTION)
        self.cache = RedisCache()
        self._ensure_indexes()
    
    def _ensure_indexes(self):
        """Gerekli indeksleri oluşturur."""
        self.db_manager.create_indexes(self.COLLECTION, [
            {"keys": [("username", 1)], "unique": True},
            {"keys": [("email", 1)], "unique": True},
            {"keys": [("role", 1)]},
            {"keys": [("status", 1)]}
        ])
    
    def _clear_user_cache(self, user_id: str):
        """Kullanıcı önbelleğini temizler."""
        self.cache.delete(f"{self.CACHE_PREFIX}{user_id}")
        self.cache.delete(f"{self.CACHE_PREFIX}username:{user_id}")
        self.cache.delete(f"{self.CACHE_PREFIX}email:{user_id}")
    
    @cached(ttl=3600, key_prefix="user_service:get_by_id")
    def get_by_id(self, user_id: str) -> Optional[User]:
        """
        ID'ye göre kullanıcı getirir.
        
        Args:
            user_id: Kullanıcı ID
            
        Returns:
            Optional[User]: Kullanıcı nesnesi veya None
        """
        user_data = self.collection.find_one({"id": user_id})
        if not user_data:
            return None
        return User.from_dict(user_data)
    
    @cached(ttl=3600, key_prefix="user_service:get_by_username")
    def get_by_username(self, username: str) -> Optional[User]:
        """
        Kullanıcı adına göre kullanıcı getirir.
        
        Args:
            username: Kullanıcı adı
            
        Returns:
            Optional[User]: Kullanıcı nesnesi veya None
        """
        user_data = self.collection.find_one({"username": username})
        if not user_data:
            return None
        return User.from_dict(user_data)
    
    @cached(ttl=3600, key_prefix="user_service:get_by_email")
    def get_by_email(self, email: str) -> Optional[User]:
        """
        E-posta adresine göre kullanıcı getirir.
        
        Args:
            email: E-posta adresi
            
        Returns:
            Optional[User]: Kullanıcı nesnesi veya None
        """
        user_data = self.collection.find_one({"email": email})
        if not user_data:
            return None
        return User.from_dict(user_data)
    
    def create(self, user_data: UserCreate) -> User:
        """
        Yeni kullanıcı oluşturur.
        
        Args:
            user_data: Kullanıcı verileri
            
        Returns:
            User: Oluşturulan kullanıcı
            
        Raises:
            HTTPException: Kullanıcı adı veya e-posta zaten kullanımdaysa
        """
        # Kullanıcı adı ve e-posta kontrol et
        if self.get_by_username(user_data.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bu kullanıcı adı zaten kullanımda"
            )
        
        if self.get_by_email(user_data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bu e-posta adresi zaten kullanımda"
            )
        
        # Kullanıcı nesnesi oluştur
        user = User(
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name,
            role=user_data.role,
            hashed_password=User.hash_password(user_data.password)
        )
        
        # Veritabanına kaydet
        try:
            self.collection.insert_one(user.to_dict())
            logger.info(f"Yeni kullanıcı oluşturuldu: {user.username}")
            return user
        except DuplicateKeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bu kullanıcı adı veya e-posta zaten kullanımda"
            )
    
    def update(self, user_id: str, user_data: UserUpdate) -> Optional[User]:
        """
        Kullanıcıyı günceller.
        
        Args:
            user_id: Kullanıcı ID
            user_data: Güncellenecek veriler
            
        Returns:
            Optional[User]: Güncellenmiş kullanıcı veya None
            
        Raises:
            HTTPException: E-posta zaten kullanımdaysa
        """
        # Kullanıcıyı kontrol et
        user = self.get_by_id(user_id)
        if not user:
            return None
        
        # Güncellenecek alanları belirle
        update_data = {}
        
        if user_data.email is not None and user_data.email != user.email:
            # E-posta değiştiriliyorsa, kullanımda mı kontrol et
            existing = self.get_by_email(user_data.email)
            if existing and existing.id != user_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Bu e-posta adresi zaten kullanımda"
                )
            update_data["email"] = user_data.email
        
        if user_data.password is not None:
            update_data["hashed_password"] = User.hash_password(user_data.password)
        
        if user_data.full_name is not None:
            update_data["full_name"] = user_data.full_name
        
        if user_data.role is not None:
            update_data["role"] = user_data.role
        
        if user_data.status is not None:
            update_data["status"] = user_data.status
        
        # Güncelleme tarihi ekle
        update_data["updated_at"] = datetime.utcnow()
        
        if not update_data:
            return user  # Güncellenecek veri yok
        
        # Veritabanını güncelle
        self.collection.update_one(
            {"id": user_id},
            {"$set": update_data}
        )
        
        # Önbelleği temizle
        self._clear_user_cache(user_id)
        
        # Güncellenmiş kullanıcıyı getir
        return self.get_by_id(user_id)
    
    def delete(self, user_id: str) -> bool:
        """
        Kullanıcıyı siler.
        
        Args:
            user_id: Kullanıcı ID
            
        Returns:
            bool: Başarılı mı
        """
        result = self.collection.delete_one({"id": user_id})
        
        if result.deleted_count > 0:
            # Önbelleği temizle
            self._clear_user_cache(user_id)
            logger.info(f"Kullanıcı silindi: {user_id}")
            return True
        
        return False
    
    def list_users(
        self, 
        skip: int = 0, 
        limit: int = 100,
        role: Optional[UserRole] = None,
        status: Optional[UserStatus] = None,
        search: Optional[str] = None
    ) -> List[User]:
        """
        Kullanıcıları listeler.
        
        Args:
            skip: Atlanacak kayıt sayısı
            limit: Maksimum kayıt sayısı
            role: Rolle filtreleme
            status: Duruma göre filtreleme
            search: Arama terimi (kullanıcı adı veya e-posta)
            
        Returns:
            List[User]: Kullanıcı listesi
        """
        # Filtre oluştur
        query = {}
        
        if role:
            query["role"] = role
        
        if status:
            query["status"] = status
        
        if search:
            query["$or"] = [
                {"username": {"$regex": search, "$options": "i"}},
                {"email": {"$regex": search, "$options": "i"}},
                {"full_name": {"$regex": search, "$options": "i"}}
            ]
        
        # Kullanıcıları getir
        users = []
        cursor = self.collection.find(query).skip(skip).limit(limit)
        
        for user_data in cursor:
            users.append(User.from_dict(user_data))
        
        return users
    
    def count_users(
        self,
        role: Optional[UserRole] = None,
        status: Optional[UserStatus] = None,
        search: Optional[str] = None
    ) -> int:
        """
        Filtrelere göre kullanıcı sayısını döndürür.
        
        Args:
            role: Rolle filtreleme
            status: Duruma göre filtreleme
            search: Arama terimi
            
        Returns:
            int: Kullanıcı sayısı
        """
        # Filtre oluştur
        query = {}
        
        if role:
            query["role"] = role
        
        if status:
            query["status"] = status
        
        if search:
            query["$or"] = [
                {"username": {"$regex": search, "$options": "i"}},
                {"email": {"$regex": search, "$options": "i"}},
                {"full_name": {"$regex": search, "$options": "i"}}
            ]
        
        # Sayım
        return self.collection.count_documents(query)
    
    def update_login_time(self, user_id: str) -> None:
        """
        Kullanıcının son giriş zamanını günceller.
        
        Args:
            user_id: Kullanıcı ID
        """
        self.collection.update_one(
            {"id": user_id},
            {"$set": {"last_login": datetime.utcnow()}}
        )
        
        # Önbelleği temizle
        self._clear_user_cache(user_id)
    
    def update_permissions(self, user_id: str, permissions: List[str]) -> Optional[User]:
        """
        Kullanıcı izinlerini günceller.
        
        Args:
            user_id: Kullanıcı ID
            permissions: İzin listesi
            
        Returns:
            Optional[User]: Güncellenmiş kullanıcı veya None
        """
        # Kullanıcıyı kontrol et
        user = self.get_by_id(user_id)
        if not user:
            return None
        
        # İzinleri güncelle
        self.collection.update_one(
            {"id": user_id},
            {
                "$set": {
                    "permissions": permissions,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        # Önbelleği temizle
        self._clear_user_cache(user_id)
        
        # Güncellenmiş kullanıcıyı getir
        return self.get_by_id(user_id)