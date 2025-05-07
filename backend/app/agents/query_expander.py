from typing import Dict, Any, List, Optional, Set
import logging
import time
import re
import json

from app.agents.base import BaseAgent
from app.services.llm_service import get_llm_service
from app.core.settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class QueryExpansionResult(BaseModel):
    """Result from query expansion."""
    original_query: str
    expanded_queries: List[str]
    rewritten_query: Optional[str] = None
    query_type: str  # 'keyword', 'natural_language', 'hybrid'
    reasoning: Optional[str] = None


class QueryExpanderAgent(BaseAgent):
    """
    Agent for expanding and rewriting queries.
    
    Performs query analysis, expansion with synonyms and related terms,
    and rewrites queries to improve retrieval performance.
    """
    
    def __init__(self):
        self.description = "Expands and rewrites queries to improve retrieval"
        self.version = "1.1"
        self.llm_service = get_llm_service()
        super().__init__()
    
    def _load_resources(self):
        """Load resources needed for query expansion."""
        # Load prompts
        self.query_analysis_prompt = """
        Analyze the following search query and determine its type:
        
        Query: "{query}"
        
        Determine if this is a:
        1. Keyword query (just some terms without proper grammar)
        2. Natural language query (proper grammatical question)
        3. Hybrid query (mix of keywords and natural language)
        
        Return your response as a JSON object with:
        - "query_type": One of "keyword", "natural_language", or "hybrid"
        - "reasoning": Brief explanation of why you classified it this way
        
        For example:
        {
          "query_type": "natural_language",
          "reasoning": "This is a complete grammatical question with a question mark."
        }
        
        Only include the JSON object, nothing else.
        """
        
        self.query_expansion_prompt = """
        Generate expanded versions of the following search query by adding synonyms, related terms, and alternate phrasings.
        
        Original query: "{query}"
        Query type: {query_type}
        
        For {language} language, generate:
        1. 3-5 expanded versions that maintain the original intent but add relevant terms
        2. 1 completely rewritten version that best expresses the query intent
        
        Return your response as a JSON object with:
        - "expanded_queries": Array of expanded query strings
        - "rewritten_query": The single best rewritten query
        
        For example:
        {
          "expanded_queries": [
            "original terms plus synonyms",
            "original with different phrasing",
            "original with domain-specific terms"
          ],
          "rewritten_query": "best possible rephrasing of query"
        }
        
        Only include the JSON object, nothing else.
        """
        
        # Language-specific examples to add to prompts
        self.language_examples = {
            "tr": {
                "keyword": "araba fiyat istanbul",
                "natural": "İstanbul'da araba fiyatları ne kadar?",
                "expanded": [
                    "araba fiyat istanbul otomobil ücret",
                    "ikinci el araba fiyatları istanbul",
                    "araç satın alma maliyeti istanbul şehri"
                ],
                "rewritten": "İstanbul'da yeni ve ikinci el araç satış fiyatları"
            },
            "en": {
                "keyword": "car price new york",
                "natural": "How much do cars cost in New York?",
                "expanded": [
                    "car price new york automobile cost",
                    "used car prices new york city",
                    "vehicle purchase cost new york area"
                ],
                "rewritten": "New and used car sales prices in New York City"
            }
        }
    
    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate that input data contains the required fields."""
        if 'query' not in input_data or not input_data['query']:
            logger.warning("Missing query in input data")
            return False
        return True
    
    async def pre_process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare the input data for processing."""
        processed_data = input_data.copy()
        
        # Set default language if not provided
        if 'language' not in processed_data:
            processed_data['language'] = settings.multilingual.default_language
        
        return processed_data
    
    async def _analyze_query(self, query: str) -> Dict[str, Any]:
        """Analyze the query to determine its type and characteristics."""
        try:
            # Use LLM to analyze query
            prompt = self.query_analysis_prompt.format(query=query)
            
            analysis = await self.llm_service.generate_json(
                prompt=prompt,
                temperature=0.1  # Low temperature for consistent results
            )
            
            if not isinstance(analysis, dict):
                logger.warning(f"Unexpected format from LLM for query analysis: {type(analysis)}")
                return {
                    "query_type": self._guess_query_type(query),
                    "reasoning": "Automatically determined based on query structure"
                }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing query: {str(e)}")
            return {
                "query_type": self._guess_query_type(query),
                "reasoning": "Automatically determined based on query structure"
            }
    
    def _guess_query_type(self, query: str) -> str:
        """Guess the query type based on structure when LLM analysis fails."""
        # Check if query ends with question mark
        if query.endswith('?'):
            return "natural_language"
        
        # Check if query contains question words
        question_words = ['what', 'who', 'where', 'when', 'why', 'how', 'is', 'are', 'can', 'could', 'would', 'should']
        if any(query.lower().startswith(word) for word in question_words):
            return "natural_language"
        
        # Check if query has proper grammar (this is a simplified check)
        words = query.split()
        if len(words) > 3 and not all(word[0].islower() for word in words[1:] if word):
            return "natural_language"
        
        # Default to keyword query
        return "keyword"
    
    async def _expand_query(self, query: str, query_type: str, language: str) -> Dict[str, Any]:
        """Expand the query with synonyms and related terms."""
        try:
            # Build prompt
            prompt = self.query_expansion_prompt.format(
                query=query,
                query_type=query_type,
                language=language
            )
            
            # Get language-specific examples if available
            if language in self.language_examples:
                examples = self.language_examples[language]
                example_text = f"\n\nExamples for {language}:\n"
                example_text += f"Keyword query: \"{examples['keyword']}\"\n"
                example_text += f"Natural language query: \"{examples['natural']}\"\n"
                example_text += f"Example expanded queries: {json.dumps(examples['expanded'])}\n"
                example_text += f"Example rewritten query: \"{examples['rewritten']}\"\n"
                
                prompt += example_text
            
            # Generate expanded queries using LLM
            expansions = await self.llm_service.generate_json(
                prompt=prompt,
                temperature=0.7  # Higher temperature for creative variations
            )
            
            if not isinstance(expansions, dict):
                logger.warning(f"Unexpected format from LLM for query expansion: {type(expansions)}")
                return {
                    "expanded_queries": [query],
                    "rewritten_query": query
                }
            
            return expansions
            
        except Exception as e:
            logger.error(f"Error expanding query: {str(e)}")
            return {
                "expanded_queries": [query],
                "rewritten_query": query
            }
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Expand and rewrite the query to improve retrieval.
        
        Args:
            input_data: Dict containing 'query' and optional 'language'
            
        Returns:
            Dict with expanded queries and query analysis
        """
        query = input_data['query']
        language = input_data['language']
        
        # Analyze the query
        analysis = await self._analyze_query(query)
        query_type = analysis.get("query_type", "keyword")
        
        # Expand the query
        expansions = await self._expand_query(query, query_type, language)
        
        # Create result
        result = {
            "original_query": query,
            "query_type": query_type,
            "reasoning": analysis.get("reasoning"),
            "expanded_queries": expansions.get("expanded_queries", [query]),
            "rewritten_query": expansions.get("rewritten_query", query),
            "language": language
        }
        
        return result
    
    async def post_process(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Clean up and finalize results."""
        # Ensure no duplicates in expanded queries
        if "expanded_queries" in result:
            unique_queries = []
            seen = set()
            
            for query in result["expanded_queries"]:
                if query.lower() not in seen and query.lower() != result["original_query"].lower():
                    unique_queries.append(query)
                    seen.add(query.lower())
            
            # Add original query at the beginning if not already there
            if result["original_query"] not in unique_queries:
                unique_queries.insert(0, result["original_query"])
            
            result["expanded_queries"] = unique_queries
        
        return result