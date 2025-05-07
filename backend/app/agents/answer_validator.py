from typing import Dict, Any, List, Optional, Set, Tuple
import logging
import re
import json
import time
from pydantic import BaseModel, Field

from app.agents.base import BaseAgent
from app.services.llm_service import get_llm_service
from app.core.settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class ValidationResult(BaseModel):
    """Model for answer validation results."""
    is_valid: bool
    confidence: float
    reasoning: str
    supported_facts: List[str] = Field(default_factory=list)
    contradictions: List[Dict[str, str]] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)
    hallucination_score: float
    factuality_score: float
    corrected_answer: Optional[str] = None


class AnswerValidatorAgent(BaseAgent):
    """
    Agent for validating generated answers against source documents.
    
    Analyzes answers to identify:
    - Factual accuracy
    - Hallucinations
    - Contradictions with source material
    - Missing important information
    """
    
    def __init__(self):
        self.description = "Validates answers against source documents for factual accuracy"
        self.version = "1.1"
        self.llm_service = get_llm_service()
        super().__init__()
    
    def _load_resources(self):
        """Load resources needed for answer validation."""
        # Define validation prompts
        self.validation_prompt = """
        You are a critical fact checker assessing the factual accuracy of an answer against source documents.
        
        Original question:
        {question}
        
        Generated answer to validate:
        {answer}
        
        Source documents:
        {sources}
        
        Analyze the answer for factual accuracy based ONLY on the provided source documents.
        Focus on:
        1. Identifying statements that are directly supported by the sources
        2. Identifying contradictions between the answer and sources
        3. Identifying hallucinations (details in the answer not present in any source)
        4. Identifying important information from sources that was omitted in the answer
        
        Return your analysis as a JSON object with the following fields:
        - "is_valid": boolean indicating overall factual validity
        - "confidence": number between 0 and 1 indicating confidence in your assessment
        - "reasoning": explanation of your validation decision
        - "supported_facts": list of facts in the answer supported by the sources
        - "contradictions": list of objects with "claim" and "reality" fields for contradictory statements
        - "missing_information": list of important facts from sources missing from the answer
        - "hallucination_score": number between 0 and 1 (where 0 means no hallucinations)
        - "factuality_score": number between 0 and 1 (overall factual accuracy)
        - "corrected_answer": improved version of the answer that corrects any issues (if needed)
        
        Only include the JSON object, nothing else.
        """
        
        self.fast_validation_prompt = """
        Verify if the generated answer is factually accurate based SOLELY on the provided source documents.
        
        Question: {question}
        
        Answer: {answer}
        
        Sources: {sources}
        
        Return a JSON object with:
        - "is_valid": boolean indicating if the answer is factually supported
        - "confidence": number from 0-1
        - "hallucination_score": number from 0-1 (0 = no hallucinations)
        - "factuality_score": number from 0-1 (1 = completely factual)
        - "issues": list of any factual issues found
        
        Only include the JSON object, nothing else.
        """
    
    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate that input data contains the required fields."""
        if 'question' not in input_data or not input_data['question']:
            logger.warning("Missing question in input data")
            return False
        
        if 'answer' not in input_data or not input_data['answer']:
            logger.warning("Missing answer in input data")
            return False
        
        if 'sources' not in input_data or not input_data['sources']:
            logger.warning("Missing sources in input data")
            return False
            
        return True
    
    async def pre_process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare the input data for validation."""
        processed_data = input_data.copy()
        
        # Format sources if they're provided as a list of objects
        if isinstance(processed_data['sources'], list):
            # Extract text content from sources
            source_texts = []
            for i, source in enumerate(processed_data['sources']):
                if isinstance(source, dict):
                    content = source.get('text', source.get('content', ''))
                    source_texts.append(f"Source {i+1}: {content}")
                elif isinstance(source, str):
                    source_texts.append(f"Source {i+1}: {source}")
            
            processed_data['formatted_sources'] = "\n\n".join(source_texts)
        else:
            processed_data['formatted_sources'] = processed_data['sources']
        
        # Determine validation mode (thorough vs fast)
        processed_data['validation_mode'] = processed_data.get('validation_mode', 'thorough')
        
        return processed_data
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate an answer against source documents.
        
        Args:
            input_data: Dict containing 'question', 'answer', 'sources', and optional 'validation_mode'
            
        Returns:
            Dict with validation results
        """
        question = input_data['question']
        answer = input_data['answer']
        formatted_sources = input_data['formatted_sources']
        validation_mode = input_data['validation_mode']
        
        # Choose validation approach based on mode
        if validation_mode == 'fast':
            validation_result = await self._perform_fast_validation(question, answer, formatted_sources)
        else:
            validation_result = await self._perform_thorough_validation(question, answer, formatted_sources)
        
        # Add metadata to result
        result = {
            "validation_result": validation_result.dict(),
            "validation_mode": validation_mode,
            "question": question,
            "answer": answer
        }
        
        return result
    
    async def _perform_thorough_validation(self, question, answer, sources) -> ValidationResult:
        """Perform thorough validation with detailed analysis."""
        try:
            # Prepare prompt
            prompt = self.validation_prompt.format(
                question=question,
                answer=answer,
                sources=sources
            )
            
            # Generate validation with LLM
            validation = await self.llm_service.generate_json(
                prompt=prompt,
                temperature=0.0  # Use deterministic output for validation
            )
            
            if not isinstance(validation, dict):
                logger.warning(f"Unexpected format from LLM for validation: {type(validation)}")
                return ValidationResult(
                    is_valid=False,
                    confidence=0.0,
                    reasoning="Failed to generate proper validation",
                    hallucination_score=1.0,
                    factuality_score=0.0
                )
            
            # Create ValidationResult from the LLM output
            try:
                result = ValidationResult(**validation)
                return result
            except Exception as e:
                logger.error(f"Error creating ValidationResult: {str(e)}")
                # Try to create a partial result with available fields
                partial_result = ValidationResult(
                    is_valid=validation.get("is_valid", False),
                    confidence=validation.get("confidence", 0.0),
                    reasoning=validation.get("reasoning", "Validation failed"),
                    hallucination_score=validation.get("hallucination_score", 1.0),
                    factuality_score=validation.get("factuality_score", 0.0),
                    corrected_answer=validation.get("corrected_answer")
                )
                return partial_result
            
        except Exception as e:
            logger.error(f"Error performing validation: {str(e)}")
            return ValidationResult(
                is_valid=False,
                confidence=0.0,
                reasoning=f"Validation failed: {str(e)}",
                hallucination_score=1.0,
                factuality_score=0.0
            )
    
    async def _perform_fast_validation(self, question, answer, sources) -> ValidationResult:
        """Perform fast validation with less detailed analysis."""
        try:
            # Prepare prompt
            prompt = self.fast_validation_prompt.format(
                question=question,
                answer=answer,
                sources=sources
            )
            
            # Generate validation with LLM
            validation = await self.llm_service.generate_json(
                prompt=prompt,
                temperature=0.0,
                max_tokens=500  # Limit response size for speed
            )
            
            if not isinstance(validation, dict):
                logger.warning(f"Unexpected format from LLM for fast validation: {type(validation)}")
                return ValidationResult(
                    is_valid=False,
                    confidence=0.0,
                    reasoning="Fast validation failed",
                    hallucination_score=1.0,
                    factuality_score=0.0
                )
            
            # Create a ValidationResult from the fast validation
            issues = validation.get("issues", [])
            issues_text = "; ".join(issues) if issues else "No specific issues found"
            
            result = ValidationResult(
                is_valid=validation.get("is_valid", False),
                confidence=validation.get("confidence", 0.0),
                reasoning=issues_text,
                hallucination_score=validation.get("hallucination_score", 1.0),
                factuality_score=validation.get("factuality_score", 0.0)
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error performing fast validation: {str(e)}")
            return ValidationResult(
                is_valid=False,
                confidence=0.0,
                reasoning=f"Fast validation failed: {str(e)}",
                hallucination_score=1.0,
                factuality_score=0.0
            )
    
    async def post_process(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Add summary information to the validation result."""
        validation_result = result.get("validation_result", {})
        
        # Add summary field based on validation results
        if "validation_result" in result:
            is_valid = validation_result.get("is_valid", False)
            factuality_score = validation_result.get("factuality_score", 0.0)
            hallucination_score = validation_result.get("hallucination_score", 1.0)
            
            if is_valid and factuality_score >= 0.9:
                summary = "VALID: Answer is factually accurate and well-supported by sources"
            elif is_valid and factuality_score >= 0.7:
                summary = "MOSTLY VALID: Answer is largely accurate with minor issues"
            elif not is_valid and hallucination_score >= 0.7:
                summary = "HALLUCINATION: Answer contains significant hallucinations"
            elif not is_valid and factuality_score <= 0.3:
                summary = "INVALID: Answer contradicts sources or lacks factual basis"
            else:
                summary = "PARTIALLY VALID: Answer has some accurate and some problematic content"
            
            result["summary"] = summary
        
        # Add confidence level
        if "validation_result" in result:
            confidence = validation_result.get("confidence", 0.0)
            if confidence >= 0.9:
                confidence_level = "very high"
            elif confidence >= 0.7:
                confidence_level = "high"
            elif confidence >= 0.5:
                confidence_level = "moderate"
            elif confidence >= 0.3:
                confidence_level = "low"
            else:
                confidence_level = "very low"
            
            result["confidence_level"] = confidence_level
        
        return result