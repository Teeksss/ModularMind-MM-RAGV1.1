import pytest
from fastapi.testclient import TestClient

def test_health_check(test_client: TestClient):
    """
    Sağlık kontrolü endpoint'ini test eder.
    """
    response = test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "uptime" in data

def test_api_docs_access(test_client: TestClient):
    """
    API dokümanlarına erişimi test eder.
    """
    response = test_client.get("/docs")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    
    response = test_client.get("/redoc")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    
    response = test_client.get("/openapi.json")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    openapi_schema = response.json()
    assert "paths" in openapi_schema
    assert "components" in openapi_schema
    assert "info" in openapi_schema