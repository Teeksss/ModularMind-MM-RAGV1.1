import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime

from app.services.feedback_analyzer import (
    analyze_feedback,
    is_candidate_for_fine_tuning,
    check_fine_tuning_threshold,
    prepare_fine_tuning_data
)


@pytest.fixture
def sample_feedback():
    """Sample feedback data for testing."""
    return {
        "id": "feedback123",
        "query_id": "query123",
        "response_id": "response123",
        "rating": 5,
        "helpful": True,
        "feedback_text": "This was very helpful!",
        "user_id": "user123",
        "timestamp": datetime.utcnow()
    }


@pytest.fixture
def sample_negative_feedback():
    """Sample negative feedback data for testing."""
    return {
        "id": "feedback456",
        "query_id": "query456",
        "response_id": "response456",
        "rating": 1,
        "helpful": False,
        "feedback_text": "This wasn't helpful at all.",
        "user_id": "user456",
        "timestamp": datetime.utcnow()
    }


@pytest.mark.asyncio
async def test_is_candidate_for_fine_tuning(sample_feedback, sample_negative_feedback):
    """Test is_candidate_for_fine_tuning function."""
    # Test positive feedback
    assert is_candidate_for_fine_tuning(sample_feedback) is True
    
    # Test negative feedback
    assert is_candidate_for_fine_tuning(sample_negative_feedback) is False
    
    # Test empty feedback
    empty_feedback = {}
    assert is_candidate_for_fine_tuning(empty_feedback) is False
    
    # Test missing key fields
    incomplete_feedback = {"rating": 4}
    assert is_candidate_for_fine_tuning(incomplete_feedback) is False


@pytest.mark.asyncio
async def test_analyze_feedback(sample_feedback):
    """Test analyze_feedback function."""
    with patch("app.services.feedback_analyzer.save_fine_tuning_candidate", new_callable=AsyncMock) as mock_save, \
         patch("app.services.feedback_analyzer.check_fine_tuning_threshold", new_callable=AsyncMock) as mock_check:
        
        await analyze_feedback(sample_feedback)
        
        # Verify save_fine_tuning_candidate was called
        mock_save.assert_called_once()
        
        # Verify check_fine_tuning_threshold was called
        mock_check.assert_called_once()


@pytest.mark.asyncio
async def test_analyze_feedback_negative(sample_negative_feedback):
    """Test analyze_feedback function with negative feedback."""
    with patch("app.services.feedback_analyzer.save_fine_tuning_candidate", new_callable=AsyncMock) as mock_save, \
         patch("app.services.feedback_analyzer.check_fine_tuning_threshold", new_callable=AsyncMock) as mock_check:
        
        await analyze_feedback(sample_negative_feedback)
        
        # Verify save_fine_tuning_candidate was NOT called for negative feedback
        mock_save.assert_not_called()
        
        # check_fine_tuning_threshold should still be called
        mock_check.assert_called_once()


@pytest.mark.asyncio
async def test_check_fine_tuning_threshold():
    """Test check_fine_tuning_threshold function."""
    # Mock the database call to return enough candidates
    mock_candidates = [{"id": f"candidate{i}"} for i in range(60)]
    
    with patch("app.services.feedback_analyzer.get_fine_tuning_candidates", new_callable=AsyncMock) as mock_get_candidates:
        mock_get_candidates.return_value = mock_candidates
        
        # In a real implementation, this would trigger fine_tuning_job scheduling
        # In our test, we just verify that the function runs without errors
        await check_fine_tuning_threshold()
        
        # Verify get_fine_tuning_candidates was called with correct parameters
        mock_get_candidates.assert_called_once()
        args, kwargs = mock_get_candidates.call_args
        assert kwargs["is_processed"] is False


@pytest.mark.asyncio
async def test_prepare_fine_tuning_data():
    """Test prepare_fine_tuning_data function."""
    # Create sample candidates
    candidates = [
        {"id": "candidate1", "query_id": "query1", "response_id": "response1", "rating": 5},
        {"id": "candidate2", "query_id": "query2", "response_id": "response2", "rating": 4},
    ]
    
    # Mock functions that would retrieve the actual query and response texts
    with patch("app.services.feedback_analyzer.get_query_text", return_value="Sample query text"), \
         patch("app.services.feedback_analyzer.get_response_text", return_value="Sample response text"):
        
        training_examples = await prepare_fine_tuning_data(candidates)
        
        # Verify that we got the expected number of examples
        assert len(training_examples) == 2
        
        # Verify structure of training examples
        for example in training_examples:
            assert "query" in example
            assert "response" in example
            assert "score" in example
            
            # Check score normalization
            score = example["score"]
            assert 0 <= score <= 1.0