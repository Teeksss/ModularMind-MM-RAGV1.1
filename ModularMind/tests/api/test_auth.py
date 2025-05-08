"""
Auth endpoint'leri için testler.
"""

import pytest
from fastapi.testclient import TestClient
from ModularMind.API.db.base import DatabaseManager
from ModularMind.API.models.user import User

def test_user_register(test_client: TestClient, test_db):
    """
    Kullanıcı kaydı testini gerçekleştirir.
    """
    # Veritabanında users koleksiyonunu temizle
    users_collection = test_db.get_collection("users")
    users_collection.delete_many({})
    
    # Test verileri
    test_data = {
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "SecurePass123!",
        "full_name": "New User"
    }
    
    # Kayıt isteği gönder
    response = test_client.post("/api/v1/auth/register", json=test_data)
    
    # Yanıtı kontrol et
    assert response.status_code == 200
    data = response.json()
    assert "user_id" in data
    assert data["message"] == "Kullanıcı başarıyla oluşturuldu"
    
    # Veritabanında kullanıcının oluşturulduğunu doğrula
    user = users_collection.find_one({"username": test_data["username"]})
    assert user is not None
    assert user["email"] == test_data["email"]
    assert user["full_name"] == test_data["full_name"]

def test_user_login(test_client: TestClient, test_db, test_user):
    """
    Kullanıcı girişi testini gerçekleştirir.
    """
    # Test kullanıcısını veritabanına ekle
    users_collection = test_db.get_collection("users")
    users_collection.insert_one(test_user)
    
    # Giriş isteği gönder
    login_data = {
        "username": test_user["username"],
        "password": "Password123!"
    }
    response = test_client.post("/api/v1/auth/login", params=login_data)
    
    # Yanıtı kontrol et
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "user" in data
    assert data["user"]["username"] == test_user["username"]

def test_get_current_user(test_client: TestClient, test_db, test_user, user_token_headers):
    """
    Mevcut kullanıcı bilgilerini alma testini gerçekleştirir.
    """
    # Test kullanıcısını veritabanına ekle
    users_collection = test_db.get_collection("users")
    users_collection.insert_one(test_user)
    
    # Kullanıcı bilgilerini al
    response = test_client.get("/api/v1/auth/me", headers=user_token_headers)
    
    # Yanıtı kontrol et
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == test_user["username"]
    assert data["email"] == test_user["email"]
    assert "hashed_password" not in data

def test_invalid_credentials(test_client: TestClient, test_db, test_user):
    """
    Geçersiz kimlik bilgileriyle giriş testini gerçekleştirir.
    """
    # Test kullanıcısını veritabanına ekle
    users_collection = test_db.get_collection("users")
    users_collection.insert_one(test_user)
    
    # Yanlış şifre ile giriş yap
    login_data = {
        "username": test_user["username"],
        "password": "WrongPassword123!"
    }
    response = test_client.post("/api/v1/auth/login", params=login_data)
    
    # Yanıtı kontrol et
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert data["detail"] == "Geçersiz kullanıcı adı veya şifre"