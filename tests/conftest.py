import os
import sys
import pytest
import asyncio
from typing import AsyncGenerator, Generator
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app
from app.db.session import get_db
from app.db.base import Base
from app.models.model_manager import get_model_manager
from app.core.config import settings

# Test database URL (use in-memory SQLite for tests)
TEST_SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


# Create test engine and session
test_engine = create_async_engine(
    TEST_SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
    class_=AsyncSession
)


# Override database dependency
async def override_get_db():
    """Override database session for tests."""
    async with TestSessionLocal() as session:
        yield session


# Override model manager for tests
class TestModelManager:
    """Mock model manager for tests."""
    
    def __init__(self):
        self.models = {}
        self.default_model_name = "test-model"
    
    async def encode(self, texts, model_name=None, **kwargs):
        """Mock encode method."""
        import numpy as np
        if isinstance(texts, str):
            texts = [texts]
        return np.random.randn(len(texts), 384)


def get_test_model_manager():
    """Get test model manager."""
    return TestModelManager()


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def setup_test_db():
    """Set up test database."""
    # Create all tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    # Drop all tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def test_client(setup_test_db) -> Generator:
    """Create a test client for the FastAPI app."""
    # Override dependencies
    app.dependency_overrides[get_db] = override_get_db
    
    # Create test client
    with TestClient(app) as client:
        yield client
    
    # Reset dependency overrides
    app.dependency_overrides = {}


@pytest.fixture
async def db_session(setup_test_db) -> AsyncGenerator:
    """Get a test database session."""
    async with TestSessionLocal() as session:
        yield session


# Test data fixtures
@pytest.fixture
def test_user_data():
    """Generate test user data."""
    return {
        "email": "test@example.com",
        "password": "testpassword123",
        "first_name": "Test",
        "last_name": "User"
    }


@pytest.fixture
def test_document_data():
    """Generate test document data."""
    return {
        "title": "Test Document",
        "content": "This is a test document with some content for testing purposes.",
        "content_type": "text/plain",
        "language": "en"
    }


# Mock objects fixtures
@pytest.fixture
def mock_retrieval_results():
    """Generate mock retrieval results."""
    from app.services.retrievers.base import SearchResult
    
    return [
        SearchResult(
            id="doc1",
            text="This is the first test document content.",
            score=0.95,
            metadata={"title": "Document 1", "source": "Test DB"}
        ),
        SearchResult(
            id="doc2",
            text="This is the second test document with different content.",
            score=0.85,
            metadata={"title": "Document 2", "source": "Test DB"}
        ),
        SearchResult(
            id="doc3",
            text="The third document has some overlapping information with document 1.",
            score=0.75,
            metadata={"title": "Document 3", "source": "Test DB"}
        )
    ]