"""
Pytest yapılandırması ve test fixture'ları.
"""

import os
import sys
import pytest
from fastapi.testclient import TestClient
from typing import Generator, Dict, Any

# Root dizinini sys.path'e ekle
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Ana uygulama modülünü import et
from main import app
from ModularMind.API.core.auth import create_access_token
from ModularMind.API.models.user import User, UserRole

@pytest.fixture(scope="function")
def test_client() -> Generator[TestClient, None, None]:
    """
    Test için FastAPI istemci nesnesi.
    """
    # Test ortamı için ortam değişkenlerini ayarla
    os.environ["ENVIRONMENT"] = "test"
    os.environ["DATABASE_URL"] = "mongodb://localhost:27017/modularmind_test"
    os.environ["JWT_SECRET_KEY"] = "test_secret_key_for_testing_purposes_only"
    
    # Test istemcisi oluştur
    client = TestClient(app)
    
    # Yield client
    yield client
    
    # Test sonrası temizlik (ihtiyaç duyulursa)

@pytest.fixture(scope="function")
def test_db():
    """
    Test için bellek içi veritabanı.
    Bu fixture, testler için izole bir veritabanı sağlar.
    """
    # Test veritabanı bağlantısını kur
    from ModularMind.API.db.base import DatabaseManager
    
    db_manager = DatabaseManager()
    
    # Test veritabanını temizle
    db = db_manager.get_database()
    for collection in db.list_collection_names():
        db[collection].delete_many({})
    
    # Test veritabanını döndür
    yield db_manager
    
    # Test sonrası temizlik
    for collection in db.list_collection_names():
        db[collection].delete_many({})

@pytest.fixture
def test_user() -> Dict[str, Any]:
    """
    Test için örnek kullanıcı verileri.
    """
    return {
        "id": "test_user_id",
        "username": "testuser",
        "email": "test@example.com",
        "full_name": "Test User",
        "role": UserRole.USER,
        "status": "active",
        "hashed_password": User.hash_password("Password123!")
    }

@pytest.fixture
def test_admin() -> Dict[str, Any]:
    """
    Test için örnek admin kullanıcı verileri.
    """
    return {
        "id": "test_admin_id",
        "username": "testadmin",
        "email": "admin@example.com",
        "full_name": "Test Admin",
        "role": UserRole.ADMIN,
        "status": "active",
        "hashed_password": User.hash_password("AdminPass123!")
    }

@pytest.fixture
def user_token_headers(test_user: Dict[str, Any]) -> Dict[str, str]:
    """
    Test için kullanıcı JWT token başlıkları.
    """
    token = create_access_token(
        data={"sub": test_user["username"], "role": test_user["role"]}
    )
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def admin_token_headers(test_admin: Dict[str, Any]) -> Dict[str, str]:
    """
    Test için admin JWT token başlıkları.
    """
    token = create_access_token(
        data={"sub": test_admin["username"], "role": test_admin["role"]}
    )
    return {"Authorization": f"Bearer {token}"}