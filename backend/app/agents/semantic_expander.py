from typing import Dict, Any, List, Optional, Set
import logging
import re
from collections import Counter

from app.agents.base import BaseAgent
from app.services.llm_service import get_llm_service
from app.core.settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class SemanticExpanderAgent(BaseAgent):
    """
    Agent for semantic expansion of content.
    
    Identifies key concepts and generates related terms, synonyms,
    and semantic variants to improve retrieval and context.
    """
    
    def __init__(self):
        self.description = "Expands content semantically with related terms and concepts"
        self.version = "1.1"
        self.llm_service = get_llm_service()
        super().__init__()
    
    def _load_resources(self):
        """Load resources needed for semantic expansion."""
        # Define expansion prompts
        self.key_concepts_prompt = """
        Identify the key concepts, entities, and technical terms from the following text.
        Focus on domain-specific terminology, important entities, and central concepts.
        
        Text:
        {document_content}
        
        Return your response as a JSON array of strings containing only the key terms.
        Example: ["artificial intelligence", "neural networks", "transformer model", "OpenAI"]
        
        Only include the JSON array, nothing else.
        """
        
        self.expansion_prompt = """
        For each of the following key concepts, provide:
        1. Synonyms or alternative phrasings
        2. Broader terms (parent concepts)
        3. Narrower terms (more specific concepts)
        4. Related concepts in the same domain
        
        Key concepts:
        {concepts}
        
        Return your response as a JSON object where each key is a concept, and the value is an object with the properties:
        - "synonyms": array of synonyms or alternative phrasings
        - "broader": array of broader terms
        - "narrower": array of narrower terms
        - "related": array of related concepts
        
        Example:
        {{
          "machine learning": {{
            "synonyms": ["ML", "statistical learning", "predictive modeling"],
            "broader": ["artificial intelligence", "computer science", "data science"],
            "narrower": ["deep learning", "reinforcement learning", "supervised learning"],
            "related": ["neural networks", "algorithms", "data mining"]
          }}
        }}
        
        Only include the JSON object, nothing else.
        """
        
        # Regex patterns for basic term extraction (backup method)
        self.noun_phrase_pattern = re.compile(r'\b([A-Z][a-z]+\s)*[A-Z][a-z]+\b|\b[a-z]+\b')
        self.stopwords = set(['the', 'and', 'or', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'with', 'by', 'of', 'is', 'are'])
    
    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate that input data contains the required fields."""
        if 'document_content' not in input_data or not input_data['document_content']:
            logger.warning("Missing document_content in input data")
            return False
        return True
    
    async def pre_process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare the document content for expansion."""
        processed_data = input_data.copy()
        
        # Limit document content to a reasonable size
        if len(processed_data['document_content']) > 15000:
            processed_data['document_content'] = processed_data['document_content'][:15000] + "..."
            logger.info("Document content truncated for semantic expansion")
        
        return processed_data
    
    async def _extract_key_concepts_with_llm(self, text: str) -> List[str]:
        """Extract key concepts using LLM."""
        try:
            # Generate concepts using LLM
            concepts = await self.llm_service.generate_json(
                prompt=self.key_concepts_prompt.format(document_content=text),
                temperature=0.0
            )
            
            if isinstance(concepts, list):
                return concepts
            
            logger.warning(f"Unexpected format from LLM for concepts: {type(concepts)}")
            return []
            
        except Exception as e:
            logger.error(f"Error extracting concepts with LLM: {str(e)}")
            return []
    
    def _extract_key_concepts_with_regex(self, text: str, max_concepts: int = 15) -> List[str]:
        """Extract key concepts using regex patterns as a fallback method."""
        # Find all noun phrases
        matches = self.noun_phrase_pattern.findall(text)
        
        # Filter out stopwords and short terms
        filtered_terms = [term.lower() for term in matches if term.lower() not in self.stopwords and len(term) > 3]
        
        # Count occurrences and get most frequent
        counter = Counter(filtered_terms)
        most_common = [term for term, _ in counter.most_common(max_concepts)]
        
        return most_common
    
    async def _expand_concepts(self, concepts: List[str]) -> Dict[str, Dict[str, List[str]]]:
        """Expand concepts with synonyms, broader/narrower terms, and related concepts."""
        if not concepts:
            return {}
        
        try:
            # Generate expansions using LLM
            expansions = await self.llm_service.generate_json(
                prompt=self.expansion_prompt.format(concepts=", ".join(concepts)),
                temperature=0.7  # Higher temperature for more diverse expansions
            )
            
            if isinstance(expansions, dict):
                return expansions
            
            logger.warning(f"Unexpected format from LLM for expansions: {type(expansions)}")
            return {}
            
        except Exception as e:
            logger.error(f"Error expanding concepts with LLM: {str(e)}")
            return {}
    
    def _normalize_expansions(self, expansions: Dict[str, Dict[str, List[str]]]) -> Dict[str, Dict[str, List[str]]]:
        """Clean and normalize concept expansions."""
        normalized = {}
        
        for concept, expansion in expansions.items():
            # Normalize concept name
            norm_concept = concept.strip().lower()
            
            # Initialize normalized expansion
            norm_expansion = {
                "synonyms": [],
                "broader": [],
                "narrower": [],
                "related": []
            }
            
            # Process each expansion category
            for category in ["synonyms", "broader", "narrower", "related"]:
                if category in expansion and isinstance(expansion[category], list):
                    # Clean terms
                    terms = [term.strip().lower() for term in expansion[category] if term.strip()]
                    
                    # Remove duplicates
                    unique_terms = list(dict.fromkeys(terms))
                    
                    # Remove the original concept from its own expansions
                    if norm_concept in unique_terms:
                        unique_terms.remove(norm_concept)
                    
                    norm_expansion[category] = unique_terms
            
            normalized[norm_concept] = norm_expansion
        
        return normalized
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Expand concepts semantically from document content.
        
        Args:
            input_data: Dict containing 'document_content' and optional parameters
            
        Returns:
            Dict with expanded concepts
        """
        document_content = input_data['document_content']
        document_id = input_data.get('document_id', 'unknown')
        max_concepts = input_data.get('max_concepts', 10)
        
        # Extract key concepts using LLM
        concepts = await self._extract_key_concepts_with_llm(document_content)
        
        # Fall back to regex extraction if LLM method fails
        if not concepts:
            logger.info("Falling back to regex-based concept extraction")
            concepts = self._extract_key_concepts_with_regex(document_content, max_concepts)
        
        # Limit to max_concepts
        concepts = concepts[:max_concepts]
        
        if not concepts:
            logger.warning(f"No concepts extracted from document {document_id}")
            return {
                "concepts": [],
                "expansions": {},
                "document_id": document_id
            }
        
        # Expand concepts
        expansions = await self._expand_concepts(concepts)
        
        # Normalize expansions
        normalized_expansions = self._normalize_expansions(expansions)
        
        return {
            "concepts": concepts,
            "expansions": normalized_expansions,
            "document_id": document_id
        }
    
    async def post_process(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance the semantic expansions with additional metadata."""
        # Compute statistics
        expansions = result.get("expansions", {})
        concepts = result.get("concepts", [])
        
        total_terms = 0
        expansion_types = ["synonyms", "broader", "narrower", "related"]
        type_counts = {t: 0 for t in expansion_types}
        
        for concept, expansion in expansions.items():
            for exp_type in expansion_types:
                terms = expansion.get(exp_type, [])
                type_counts[exp_type] += len(terms)
                total_terms += len(terms)
        
        # Add metadata to result
        result["metadata"] = {
            "total_concepts": len(concepts),
            "total_expanded_terms": total_terms,
            "average_terms_per_concept": total_terms / len(concepts) if concepts else 0,
            "term_type_distribution": type_counts
        }
        
        return result