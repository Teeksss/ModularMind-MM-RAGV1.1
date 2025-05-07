from typing import Dict, Any, List, Optional, Set
import logging
import re
from collections import Counter

from app.agents.base import BaseAgent
from app.services.llm_service import get_llm_service
from app.core.settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class ContextualTaggerAgent(BaseAgent):
    """
    Agent for contextual tagging of documents.
    
    Analyzes documents to generate relevant tags, categories,
    and contextual information based on content.
    """
    
    def __init__(self):
        self.description = "Tags documents based on contextual analysis"
        self.version = "1.1"
        self.llm_service = get_llm_service()
        super().__init__()
    
    def _load_resources(self):
        """Load resources needed for tagging."""
        # Define tagging prompts
        self.general_tagging_prompt = """
        Analyze the following document and generate relevant tags for it.
        Focus on the main topics, themes, and important concepts in the document.
        
        Document:
        {document_content}
        
        Return your response as a JSON object with:
        1. "general_tags": An array of general topic tags
        2. "specific_tags": An array of more specific or technical tags
        3. "categories": An array of broader categories this document falls under
        
        For example:
        {
          "general_tags": ["finance", "investment", "banking"],
          "specific_tags": ["portfolio management", "risk assessment", "market analysis"],
          "categories": ["financial services", "business"]
        }
        
        Only include the JSON object, nothing else.
        """
        
        self.sector_tagging_prompt = """
        Identify the most relevant industry sectors or domains for the following document.
        
        Document:
        {document_content}
        
        Return your response as a JSON object with:
        1. "primary_sector": The main sector/industry this document relates to
        2. "related_sectors": Array of other related sectors
        3. "confidence": A number between 0 and 1 indicating your confidence in this classification
        
        For example:
        {
          "primary_sector": "healthcare",
          "related_sectors": ["pharmaceuticals", "medical devices", "health insurance"],
          "confidence": 0.85
        }
        
        Only include the JSON object, nothing else.
        """
        
        self.entity_tagging_prompt = """
        Extract the main entities from the following document.
        Focus on organizations, people, products, locations, and other named entities.
        
        Document:
        {document_content}
        
        Return your response as a JSON object with categories of entities:
        1. "organizations": Array of organization names
        2. "people": Array of person names
        3. "products": Array of product names
        4. "locations": Array of location names
        5. "other": Array of other important named entities
        
        For example:
        {
          "organizations": ["Microsoft", "Google", "Apple"],
          "people": ["Satya Nadella", "Sundar Pichai"],
          "products": ["Windows 11", "Google Cloud"],
          "locations": ["Silicon Valley", "Seattle"],
          "other": ["AI", "cloud computing"]
        }
        
        Only include the JSON object, nothing else.
        """
        
        # Certain languages might need special treatment
        self.lang_specific_prompts = {
            "tr": {
                "general": """
                Aşağıdaki belgeyi analiz edin ve ilgili etiketler oluşturun.
                Belgedeki ana konulara, temalara ve önemli kavramlara odaklanın.
                
                Belge:
                {document_content}
                
                Yanıtınızı şu alanları içeren bir JSON nesnesi olarak döndürün:
                1. "general_tags": Genel konu etiketleri dizisi
                2. "specific_tags": Daha spesifik veya teknik etiketler dizisi
                3. "categories": Bu belgenin ait olduğu daha geniş kategoriler dizisi
                
                Örneğin:
                {
                  "general_tags": ["finans", "yatırım", "bankacılık"],
                  "specific_tags": ["portföy yönetimi", "risk değerlendirmesi", "piyasa analizi"],
                  "categories": ["finansal hizmetler", "iş dünyası"]
                }
                
                Sadece JSON nesnesini içerin, başka bir şey eklemeyin.
                """
            }
        }
    
    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate that input data contains the required fields."""
        if 'document_content' not in input_data or not input_data['document_content']:
            logger.warning("Missing document_content in input data")
            return False
        return True
    
    async def pre_process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare the document content for tagging."""
        processed_data = input_data.copy()
        
        # Limit document content to a reasonable size
        if len(processed_data['document_content']) > 8000:
            processed_data['document_content'] = processed_data['document_content'][:8000] + "..."
            logger.info("Document content truncated for tagging")
        
        return processed_data
    
    def _get_tagging_prompt(self, prompt_type: str, language: str) -> str:
        """Get the appropriate tagging prompt based on language."""
        # Check if we have a language-specific prompt
        if language in self.lang_specific_prompts and prompt_type in self.lang_specific_prompts[language]:
            return self.lang_specific_prompts[language][prompt_type]
        
        # Otherwise use default prompts
        if prompt_type == "general":
            return self.general_tagging_prompt
        elif prompt_type == "sector":
            return self.sector_tagging_prompt
        elif prompt_type == "entity":
            return self.entity_tagging_prompt
        
        # Default to general prompt
        return self.general_tagging_prompt
    
    async def _tag_general(self, text: str, language: str) -> Dict[str, Any]:
        """Generate general tags for the document."""
        prompt = self._get_tagging_prompt("general", language).format(document_content=text)
        
        try:
            result = await self.llm_service.generate_json(
                prompt=prompt,
                temperature=0.2  # Low temperature for consistent results
            )
            
            if not isinstance(result, dict):
                logger.warning(f"Unexpected format from LLM for general tags: {type(result)}")
                return {
                    "general_tags": [],
                    "specific_tags": [],
                    "categories": []
                }
            
            return {
                "general_tags": result.get("general_tags", []),
                "specific_tags": result.get("specific_tags", []),
                "categories": result.get("categories", [])
            }
            
        except Exception as e:
            logger.error(f"Error generating general tags: {str(e)}")
            return {
                "general_tags": [],
                "specific_tags": [],
                "categories": []
            }
    
    async def _tag_sector(self, text: str, language: str) -> Dict[str, Any]:
        """Identify industry sectors for the document."""
        prompt = self._get_tagging_prompt("sector", language).format(document_content=text)
        
        try:
            result = await self.llm_service.generate_json(
                prompt=prompt,
                temperature=0.1  # Lower temperature for more deterministic results
            )
            
            if not isinstance(result, dict):
                logger.warning(f"Unexpected format from LLM for sector tags: {type(result)}")
                return {
                    "primary_sector": "unknown",
                    "related_sectors": [],
                    "confidence": 0.0
                }
            
            return {
                "primary_sector": result.get("primary_sector", "unknown"),
                "related_sectors": result.get("related_sectors", []),
                "confidence": result.get("confidence", 0.0)
            }
            
        except Exception as e:
            logger.error(f"Error identifying sectors: {str(e)}")
            return {
                "primary_sector": "unknown",
                "related_sectors": [],
                "confidence": 0.0
            }
    
    async def _tag_entities(self, text: str, language: str) -> Dict[str, List[str]]:
        """Extract entities from the document."""
        prompt = self._get_tagging_prompt("entity", language).format(document_content=text)
        
        try:
            result = await self.llm_service.generate_json(
                prompt=prompt,
                temperature=0.2
            )
            
            if not isinstance(result, dict):
                logger.warning(f"Unexpected format from LLM for entities: {type(result)}")
                return {
                    "organizations": [],
                    "people": [],
                    "products": [],
                    "locations": [],
                    "other": []
                }
            
            return {
                "organizations": result.get("organizations", []),
                "people": result.get("people", []),
                "products": result.get("products", []),
                "locations": result.get("locations", []),
                "other": result.get("other", [])
            }
            
        except Exception as e:
            logger.error(f"Error extracting entities: {str(e)}")
            return {
                "organizations": [],
                "people": [],
                "products": [],
                "locations": [],
                "other": []
            }
    
    def _normalize_tags(self, tags: List[str]) -> List[Dict[str, Any]]:
        """Normalize and clean tags."""
        normalized = []
        
        for tag in tags:
            # Clean up tag
            clean_tag = tag.strip().lower()
            
            # Skip very short tags
            if len(clean_tag) < 2:
                continue
            
            # Add to normalized list with default confidence
            normalized.append({
                "tag": clean_tag,
                "confidence": 1.0
            })
        
        return normalized
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process document and generate tags.
        
        Args:
            input_data: Dict containing 'document_content' and optional parameters
            
        Returns:
            Dict with tags and entities
        """
        document_content = input_data['document_content']
        document_id = input_data.get('document_id', 'unknown')
        
        # Get document language or use default
        language = input_data.get('language', settings.multilingual.default_language)
        
        # Generate general tags
        general_tags_result = await self._tag_general(document_content, language)
        
        # Identify sectors
        sector_result = await self._tag_sector(document_content, language)
        
        # Extract entities
        entities_result = await self._tag_entities(document_content, language)
        
        # Combine all tags
        all_tags = []
        
        # Add general tags
        for tag in general_tags_result.get("general_tags", []):
            all_tags.append({
                "tag": tag,
                "category": "general",
                "confidence": 0.9
            })
        
        # Add specific tags
        for tag in general_tags_result.get("specific_tags", []):
            all_tags.append({
                "tag": tag,
                "category": "specific",
                "confidence": 0.8
            })
        
        # Add category tags
        for tag in general_tags_result.get("categories", []):
            all_tags.append({
                "tag": tag,
                "category": "category",
                "confidence": 0.9
            })
        
        # Add sector tags
        if sector_result.get("primary_sector") and sector_result.get("primary_sector") != "unknown":
            all_tags.append({
                "tag": sector_result["primary_sector"],
                "category": "sector",
                "confidence": sector_result.get("confidence", 0.7)
            })
        
        for tag in sector_result.get("related_sectors", []):
            all_tags.append({
                "tag": tag,
                "category": "sector",
                "confidence": sector_result.get("confidence", 0.7) * 0.8  # Slightly lower confidence for related sectors
            })
        
        # Prepare result
        result = {
            "tags": all_tags,
            "entities": entities_result,
            "sectors": sector_result,
            "document_id": document_id,
            "language": language
        }
        
        return result
    
    async def post_process(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Clean up and normalize the tags."""
        if "tags" not in result:
            return result
        
        # Remove duplicate tags
        unique_tags = {}
        for tag_entry in result["tags"]:
            # Create a unique key for the tag
            tag_key = tag_entry["tag"].lower()
            
            # If this tag is new or has higher confidence than previous one, update it
            if tag_key not in unique_tags or tag_entry["confidence"] > unique_tags[tag_key]["confidence"]:
                unique_tags[tag_key] = tag_entry
        
        # Convert back to list
        result["tags"] = list(unique_tags.values())
        
        return result