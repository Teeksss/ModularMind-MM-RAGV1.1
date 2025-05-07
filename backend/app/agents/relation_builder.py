from typing import Dict, Any, List, Optional, Tuple
import logging
import re
import json
import uuid
from datetime import datetime

from app.agents.base import BaseAgent
from app.services.llm_service import get_llm_service
from app.db.session import get_db
from app.core.settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class RelationBuilderAgent(BaseAgent):
    """
    Agent for extracting and building relationships between concepts and documents.
    
    This agent identifies various types of relationships:
    - Concept to concept (e.g., "X is a type of Y")
    - Document to document (e.g., "Document A references Document B")
    - Concept to value (e.g., "Price of X is $100")
    
    These relationships are stored in a knowledge graph for enhanced retrieval.
    """
    
    def __init__(self):
        self.description = "Extracts and builds relationships between concepts and documents"
        self.version = "1.1"
        self.llm_service = get_llm_service()
        super().__init__()
    
    def _load_resources(self):
        """Load resources needed for relationship extraction."""
        # Define relation extraction prompts
        self.concept_relation_prompt = """
        Extract important relationships between concepts, entities, and facts from the following text.
        Focus on relationships like:
        - "X is a type of Y"
        - "X is part of Y"
        - "X causes Y"
        - "X is used for Y"
        - "X contradicts Y"
        - "X happens before Y"
        
        Text:
        {document_content}
        
        Return your response as a JSON array of relationship objects, each with:
        - "source": the source concept/entity
        - "relation_type": the type of relationship
        - "target": the target concept/entity
        - "confidence": a number between 0.0 and 1.0 indicating confidence in this relation
        - "context": a brief text snippet from the document showing this relationship
        
        Example:
        [
          {
            "source": "transformer model",
            "relation_type": "is_type_of",
            "target": "neural network architecture",
            "confidence": 0.95,
            "context": "Transformer models are a type of neural network architecture that have revolutionized NLP tasks."
          }
        ]
        
        Only include the JSON array, nothing else.
        """
        
        self.concept_value_prompt = """
        Extract important relationships between concepts and their specific values or attributes from the following text.
        Focus on relationships like:
        - Dates associated with events or releases
        - Numerical values such as prices, metrics, measurements
        - Status values
        - Locations
        - Named entities associated with concepts
        
        Text:
        {document_content}
        
        Return your response as a JSON array of concept-value relationship objects, each with:
        - "concept": the concept or entity
        - "attribute": the type of attribute (e.g., "date", "price", "location")
        - "value": the specific value
        - "confidence": a number between 0.0 and 1.0 indicating confidence
        - "context": a brief text snippet from the document showing this relationship
        
        Example:
        [
          {
            "concept": "GPT-4",
            "attribute": "release_date",
            "value": "March 14, 2023",
            "confidence": 0.9,
            "context": "GPT-4 was officially released by OpenAI on March 14, 2023."
          }
        ]
        
        Only include the JSON array, nothing else.
        """
        
        # Regex patterns for validation
        self.date_pattern = re.compile(r'\b\d{1,2}[./]\d{1,2}[./]\d{2,4}\b|\b\d{4}-\d{2}-\d{2}\b')
        self.number_pattern = re.compile(r'\b\d+(?:\.\d+)?\b')
    
    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate that input data contains the required fields."""
        if 'document_content' not in input_data or not input_data['document_content']:
            logger.warning("Missing document_content in input data")
            return False
        
        if 'document_id' not in input_data:
            logger.warning("Missing document_id in input data")
            return False
            
        return True
    
    async def pre_process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare the document content for relation extraction."""
        processed_data = input_data.copy()
        
        # Limit document content to a reasonable size
        if len(processed_data['document_content']) > 8000:
            processed_data['document_content'] = processed_data['document_content'][:8000] + "..."
            logger.info("Document content truncated for relation extraction")
        
        return processed_data
    
    async def _extract_concept_relations(self, text: str) -> List[Dict[str, Any]]:
        """Extract concept-to-concept relations using LLM."""
        try:
            # Generate relations using LLM
            relations = await self.llm_service.generate_json(
                prompt=self.concept_relation_prompt.format(document_content=text),
                temperature=0.1
            )
            
            if isinstance(relations, list):
                # Validate relations format
                valid_relations = []
                for rel in relations:
                    if all(k in rel for k in ["source", "relation_type", "target", "confidence"]):
                        valid_relations.append(rel)
                
                return valid_relations
            
            logger.warning(f"Unexpected format from LLM for relations: {type(relations)}")
            return []
            
        except Exception as e:
            logger.error(f"Error extracting concept relations with LLM: {str(e)}")
            return []
    
    async def _extract_concept_values(self, text: str) -> List[Dict[str, Any]]:
        """Extract concept-to-value relations using LLM."""
        try:
            # Generate concept-value relations using LLM
            relations = await self.llm_service.generate_json(
                prompt=self.concept_value_prompt.format(document_content=text),
                temperature=0.1
            )
            
            if isinstance(relations, list):
                # Validate relations format
                valid_relations = []
                for rel in relations:
                    if all(k in rel for k in ["concept", "attribute", "value", "confidence"]):
                        valid_relations.append(rel)
                
                return valid_relations
            
            logger.warning(f"Unexpected format from LLM for concept-values: {type(relations)}")
            return []
            
        except Exception as e:
            logger.error(f"Error extracting concept-value relations with LLM: {str(e)}")
            return []
    
    async def _validate_and_normalize_relations(
        self, 
        concept_relations: List[Dict[str, Any]], 
        concept_values: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Validate and normalize relations."""
        # Process concept-to-concept relations
        normalized_concept_relations = []
        for rel in concept_relations:
            # Skip if confidence is too low
            if rel.get("confidence", 0) < 0.4:
                continue
                
            # Normalize relation type
            relation_type = rel["relation_type"].lower()
            relation_type = re.sub(r'[^a-z_]', '_', relation_type)
            
            normalized_concept_relations.append({
                "source": rel["source"].strip().lower(),
                "relation_type": relation_type,
                "target": rel["target"].strip().lower(),
                "confidence": float(rel["confidence"]),
                "context": rel.get("context", "")
            })
        
        # Process concept-to-value relations
        normalized_concept_values = []
        for rel in concept_values:
            # Skip if confidence is too low
            if rel.get("confidence", 0) < 0.4:
                continue
                
            # Normalize attribute type
            attribute = rel["attribute"].lower()
            attribute = re.sub(r'[^a-z_]', '_', attribute)
            
            # Validate values based on attribute type
            value = rel["value"]
            if attribute in ["date", "release_date", "created_date", "modified_date"]:
                if not self.date_pattern.search(str(value)):
                    # Not a valid date format, skip or fix
                    continue
            
            if attribute in ["price", "cost", "amount", "quantity", "count"]:
                if not self.number_pattern.search(str(value)):
                    # Not a valid number format, skip or fix
                    continue
            
            normalized_concept_values.append({
                "concept": rel["concept"].strip().lower(),
                "attribute": attribute,
                "value": value,
                "confidence": float(rel["confidence"]),
                "context": rel.get("context", "")
            })
        
        return normalized_concept_relations, normalized_concept_values
    
    async def _store_relations(
        self, 
        document_id: str, 
        concept_relations: List[Dict[str, Any]], 
        concept_values: List[Dict[str, Any]]
    ) -> None:
        """Store relations in the database."""
        # Only proceed if there are relations to store
        if not concept_relations and not concept_values:
            return
        
        try:
            async with get_db() as db:
                # Store concept-to-concept relations
                for rel in concept_relations:
                    relation_id = str(uuid.uuid4())
                    
                    query = """
                    INSERT INTO document_relations (
                        id, source_id, relation_type, confidence, metadata, created_at,
                        concept_name, concept_value
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    """
                    
                    metadata = {
                        "source_concept": rel["source"],
                        "target_concept": rel["target"],
                        "context": rel.get("context", ""),
                        "extraction_method": "llm"
                    }
                    
                    values = (
                        relation_id,
                        document_id,
                        rel["relation_type"],
                        rel["confidence"],
                        json.dumps(metadata),
                        datetime.now(),
                        rel["source"],
                        rel["target"]
                    )
                    
                    await db.execute(query, *values)
                
                # Store concept-to-value relations
                for rel in concept_values:
                    relation_id = str(uuid.uuid4())
                    
                    query = """
                    INSERT INTO document_relations (
                        id, source_id, relation_type, confidence, metadata, created_at,
                        concept_name, concept_value
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    """
                    
                    metadata = {
                        "attribute": rel["attribute"],
                        "context": rel.get("context", ""),
                        "extraction_method": "llm"
                    }
                    
                    values = (
                        relation_id,
                        document_id,
                        rel["attribute"],
                        rel["confidence"],
                        json.dumps(metadata),
                        datetime.now(),
                        rel["concept"],
                        str(rel["value"])
                    )
                    
                    await db.execute(query, *values)
        
        except Exception as e:
            logger.error(f"Error storing relations: {str(e)}")
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract and build relationships from document content.
        
        Args:
            input_data: Dict containing 'document_content' and 'document_id'
            
        Returns:
            Dict with extracted relationships
        """
        document_content = input_data['document_content']
        document_id = input_data['document_id']
        
        # Extract concept-to-concept relations
        concept_relations = await self._extract_concept_relations(document_content)
        
        # Extract concept-to-value relations
        concept_values = await self._extract_concept_values(document_content)
        
        # Validate and normalize relations
        normalized_concept_relations, normalized_concept_values = await self._validate_and_normalize_relations(
            concept_relations, concept_values
        )
        
        # Store relations in database
        await self._store_relations(document_id, normalized_concept_relations, normalized_concept_values)
        
        # Return relations
        result = {
            "document_id": document_id,
            "relations": {
                "concept_relations": normalized_concept_relations,
                "concept_values": normalized_concept_values
            },
            "total_relations": len(normalized_concept_relations) + len(normalized_concept_values)
        }
        
        return result
    
    async def post_process(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Group and classify relations."""
        if "relations" not in result:
            return result
        
        concept_relations = result["relations"].get("concept_relations", [])
        concept_values = result["relations"].get("concept_values", [])
        
        # Group concept relations by type
        relation_types = {}
        for rel in concept_relations:
            rel_type = rel["relation_type"]
            if rel_type not in relation_types:
                relation_types[rel_type] = []
            relation_types[rel_type].append(rel)
        
        # Group concept values by attribute
        attribute_types = {}
        for rel in concept_values:
            attr_type = rel["attribute"]
            if attr_type not in attribute_types:
                attribute_types[attr_type] = []
            attribute_types[attr_type].append(rel)
        
        # Add classified relations to result
        result["classified_relations"] = {
            "by_relation_type": relation_types,
            "by_attribute_type": attribute_types
        }
        
        return result