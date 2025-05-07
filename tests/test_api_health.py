import pytest
from fastapi.testclient import TestClient
import json
from datetime import datetime, timedelta

from app.main import app
from app.core.config import settings

client = TestClient(app)

def test_basic_health_check():
    """Test basic health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "healthy"
    assert "version" in data
    assert "timestamp" in data


def test_readiness_probe():
    """Test readiness probe endpoint."""
    response = client.get("/health/readiness")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "database" in data
    assert "timestamp" in data


def test_liveness_probe():
    """Test liveness probe endpoint."""
    response = client.get("/health/liveness")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "system" in data
    assert "timestamp" in data


def test_detailed_health_check():
    """Test detailed health check endpoint."""
    response = client.get("/health/detailed")
    
    # Even if some components are unhealthy, the endpoint should return
    assert response.status_code in [200, 503]
    data = response.json()
    assert "status" in data
    assert "database" in data
    assert "vector_store" in data
    assert "models" in data
    assert "llm" in data
    assert "system" in data
    assert "environment" in data
    assert "version" in data
    assert "timestamp" in data


def test_models_health_check():
    """Test models health check endpoint."""
    response = client.get("/health/models")
    assert response.status_code == 200
    data = response.json()
    assert "embedding_models" in data
    assert "llm_models" in data
    assert "test_results" in data