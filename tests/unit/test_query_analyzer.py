import pytest
import os
import sys
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.agents.query_expander import QueryExpanderAgent


@pytest.mark.unit
class TestQueryExpanderAgent:
    """Test suite for the QueryExpanderAgent class."""
    
    @pytest.fixture
    def agent(self):
        """Create an instance of the agent for testing."""
        agent = QueryExpanderAgent()
        # Mock the LLM service
        agent.llm_service = MagicMock()
        return agent
    
    @pytest.mark.asyncio
    async def test_validate_input(self, agent):
        """Test the input validation."""
        # Valid input
        valid_input = {"query": "test query", "language": "en"}
        assert await agent.validate_input(valid_input) == True
        
        # Invalid input - missing query
        invalid_input = {"language": "en"}
        assert await agent.validate_input(invalid_input) == False
        
        # Invalid input - empty query
        invalid_input = {"query": "", "language": "en"}
        assert await agent.validate_input(invalid_input) == False
    
    @pytest.mark.asyncio
    async def test_pre_process(self, agent):
        """Test the pre-processing step."""
        # Input with language
        input_data = {"query": "test query", "language": "en"}
        processed = await agent.pre_process(input_data)
        assert processed["query"] == "test query"
        assert processed["language"] == "en"
        assert processed["analyze_type"] == True
        
        # Input without language
        input_data = {"query": "test query"}
        processed = await agent.pre_process(input_data)
        assert processed["language"] == "en"  # Default
    
    @pytest.mark.asyncio
    async def test_process_keyword_query(self, agent):
        """Test processing a keyword query."""
        # Mock LLM responses
        agent.llm_service.generate_json.return_value = {
            "query_type": "keyword",
            "reasoning": "Simple keyword query",
            "expanded_query": "test query expanded"
        }
        
        input_data = {
            "query": "test query",
            "language": "en",
            "analyze_type": True
        }
        
        result = await agent.process(input_data)
        
        # Check that LLM was called with the right prompt
        agent.llm_service.generate_json.assert_called_once()
        prompt_arg = agent.llm_service.generate_json.call_args[1]["prompt"]
        assert "test query" in prompt_arg
        
        # Check result
        assert result["query_type"] == "keyword"
        assert "expanded_query" in result
        assert result["expanded_query"] == "test query expanded"
    
    @pytest.mark.asyncio
    async def test_process_natural_language_query(self, agent):
        """Test processing a natural language query."""
        # Mock LLM responses
        agent.llm_service.generate_json.return_value = {
            "query_type": "natural_language",
            "reasoning": "Complex question",
            "expanded_query": "test question expanded with context",
            "keywords": ["test", "question", "context"]
        }
        
        input_data = {
            "query": "What is the test question?",
            "language": "en",
            "analyze_type": True
        }
        
        result = await agent.process(input_data)
        
        # Check result
        assert result["query_type"] == "natural_language"
        assert "expanded_query" in result
        assert "keywords" in result
        assert len(result["keywords"]) == 3
    
    @pytest.mark.asyncio
    async def test_post_process(self, agent):
        """Test the post-processing step."""
        # Raw process output
        process_output = {
            "query_type": "keyword",
            "expanded_query": "test query expanded",
            "reasoning": "Simple keyword query"
        }
        
        # Post-process
        post_processed = await agent.post_process(process_output)
        
        # Check fields and formatting
        assert post_processed["query_type"] == "keyword"
        assert post_processed["expanded_query"] == "test query expanded"
        assert "execution_time" in post_processed
        
        # Check that reasoning is preserved
        assert post_processed["reasoning"] == "Simple keyword query"