import pytest
from fastapi.testclient import TestClient
import json
from datetime import datetime, timedelta

from app.main import app
from app.core.config import settings
from app.core.security import create_access_token

client = TestClient(app)

@pytest.fixture
def test_user():
    """Test user data."""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123"
    }


@pytest.fixture
def test_token(test_user):
    """Create a test JWT token."""
    token_data = {
        "sub": test_user["username"],
        "email": test_user["email"]
    }
    return create_access_token(token_data)


def test_login(monkeypatch, test_user):
    """Test login endpoint."""
    # Mock the user verification function
    async def mock_authenticate_user(*args, **kwargs):
        return {
            "id": "user123",
            "username": test_user["username"],
            "email": test_user["email"],
            "is_active": True
        }
    
    monkeypatch.setattr("app.api.v1.endpoints.auth.authenticate_user", mock_authenticate_user)
    
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": test_user["username"],
            "password": test_user["password"]
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "token_type" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_credentials(monkeypatch, test_user):
    """Test login with invalid credentials."""
    # Mock the user verification function to return None (authentication failure)
    async def mock_authenticate_user(*args, **kwargs):
        return None
    
    monkeypatch.setattr("app.api.v1.endpoints.auth.authenticate_user", mock_authenticate_user)
    
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": test_user["username"],
            "password": "wrongpassword"
        }
    )
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert "Incorrect username or password" in data["detail"]


def test_token_refresh(monkeypatch, test_token, test_user):
    """Test token refresh endpoint."""
    # Mock the user retrieval function
    async def mock_get_user_by_username(*args, **kwargs):
        return {
            "id": "user123",
            "username": test_user["username"],
            "email": test_user["email"],
            "is_active": True
        }
    
    monkeypatch.setattr("app.api.v1.endpoints.auth.get_user_by_username", mock_get_user_by_username)
    
    response = client.post(
        "/api/v1/auth/refresh",
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "token_type" in data
    assert data["token_type"] == "bearer"


def test_get_current_user(monkeypatch, test_token, test_user):
    """Test get current user endpoint."""
    # Mock the user retrieval function
    async def mock_get_user_by_username(*args, **kwargs):
        return {
            "id": "user123",
            "username": test_user["username"],
            "email": test_user["email"],
            "is_active": True,
            "created_at": datetime.utcnow().isoformat()
        }
    
    monkeypatch.setattr("app.api.deps.get_user_by_username", mock_get_user_by_username)
    
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {test_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "username" in data
    assert data["username"] == test_user["username"]
    assert "email" in data
    assert data["email"] == test_user["email"]
    assert "password" not in data  # Ensure password is not returned


def test_get_current_user_invalid_token():
    """Test get current user with invalid token."""
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalidtoken"}
    )
    assert response.status_code == 401