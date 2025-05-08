import pytest
from fastapi.testclient import TestClient
import os
import sys
from typing import Generator

# ModularMind modülünün yolu
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app  # main.py'deki app instance'ını import et

@pytest.fixture(scope="module")
def test_client() -> Generator[TestClient, None, None]:
    """
    Test için FastAPI istemci oluşturur.
    """
    # Test veritabanı gibi test özelinde yapılandırmalar burada yapılabilir
    os.environ["ENVIRONMENT"] = "test"
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    
    # Test istemcisi oluştur
    with TestClient(app) as client:
        yield client
    
    # Test sonrası temizlik işlemleri

@pytest.fixture(scope="module")
def test_auth_headers() -> dict:
    """
    Test için kimlik doğrulama başlıkları oluşturur.
    
    Returns:
        dict: Authorization başlığı içeren sözlük
    """
    # Test JWT tokeni oluştur (gerçek bir token üretme mantığı burada olabilir)
    test_token = "test_jwt_token"
    return {"Authorization": f"Bearer {test_token}"}

@pytest.fixture
def test_document_content() -> str:
    """
    Test için örnek belge içeriği.
    """
    return """
    # ModularMind Test Document
    
    This is a sample document for testing purposes.
    
    ## Features
    
    - Feature 1
    - Feature 2
    - Feature 3
    
    ## Examples
    
    Here are some examples of using the system.
    """