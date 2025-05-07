import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Union

from app.agents.base import BaseAgent, AgentResult
from app.core.config import settings
from app.services.llm_service import get_llm_service

logger = logging.getLogger(__name__)


class AnswerValidatorAgent(BaseAgent):
    """
    Agent for validating LLM answers against source documents.
    
    This agent checks if the answer:
    1. Is factually consistent with the sources
    2. Contains no hallucinations
    3. Cites sources correctly
    4. Addresses the query directly
    """
    
    def __init__(self, name: str = "AnswerValidatorAgent"):
        """Initialize the answer validator agent."""
        super().__init__(name=name)
        self.llm_service = get_llm_service()
    
    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """
        Validate that input contains all necessary data.
        
        Args:
            input_data: Dictionary containing input data
            
        Returns:
            bool: Whether input is valid
        """
        required_fields = ["question", "answer"]
        
        if not all(field in input_data for field in required_fields):
            logger.warning(f"Missing required fields for {self.name}. Required: {required_fields}")
            return False
        
        if not input_data.get("sources") and not input_data.get("source_texts"):
            logger.warning(f"Missing either 'sources' or 'source_texts' for {self.name}")
            return False
        
        return True
    
    async def pre_process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Pre-process input data before running the agent.
        
        Args:
            input_data: Dictionary containing input data
            
        Returns:
            Dict: Processed input data
        """
        processed_data = input_data.copy()
        
        # If sources are provided as objects, extract their text content
        if "sources" in processed_data and isinstance(processed_data["sources"], list):
            if all(isinstance(source, str) for source in processed_data["sources"]):
                # Sources are already strings
                processed_data["source_texts"] = processed_data["sources"]
            else:
                # Extract text from source objects
                processed_data["source_texts"] = []
                for source in processed_data["sources"]:
                    if hasattr(source, "text"):
                        processed_data["source_texts"].append(source.text)
                    elif isinstance(source, dict) and "text" in source:
                        processed_data["source_texts"].append(source["text"])
        
        # Ensure source_texts is available
        if "source_texts" not in processed_data or not processed_data["source_texts"]:
            logger.warning(f"No valid source texts found in input for {self.name}")
            processed_data["source_texts"] = ["No sources provided"]
        
        return processed_data
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the validation request.
        
        Args:
            input_data: Dictionary containing:
                - question: The original question
                - answer: The answer to validate
                - source_texts: List of source texts
                
        Returns:
            Dict containing validation results
        """
        start_time = time.time()
        
        question = input_data["question"]
        answer = input_data["answer"]
        source_texts = input_data["source_texts"]
        
        # Combine source texts with index numbers for the prompt
        indexed_sources = ""
        for i, source in enumerate(source_texts, 1):
            indexed_sources += f"SOURCE {i}:\n{source}\n\n"
        
        # Create validation prompt
        system_prompt = """You are a helpful assistant that evaluates the factual accuracy and relevance of answers. 
Your task is to determine if an answer is:
1. Factually consistent with the provided sources
2. Directly addresses the original question
3. Free from unsupported claims or hallucinations

Evaluate the answer based ONLY on the provided sources. If information in the answer is not in the sources, 
it should be considered unsupported, even if you know it's correct."""

        user_prompt = f"""QUESTION: {question}

ANSWER TO EVALUATE:
{answer}

SOURCES:
{indexed_sources}

Evaluate the answer and provide scores on a scale of 0-10 for the following:
1. Factual Accuracy: Is the information in the answer supported by the sources?
2. Relevance: Does the answer directly address the question?
3. Completeness: Does the answer cover the key information from sources needed to answer the question?
4. Hallucination: Are there claims in the answer not supported by the sources? (0 = many unsupported claims, 10 = no unsupported claims)

For each factual claim in the answer, indicate whether it is SUPPORTED or UNSUPPORTED by the sources.
If UNSUPPORTED, explain what information is missing or contradicted.

Format your response as a JSON object with these fields:
- factuality_score (0-10 float)
- relevance_score (0-10 float)
- completeness_score (0-10 float)
- hallucination_score (0-10 float)
- overall_score (0-10 float, weighted average with factuality and hallucination weighted most heavily)
- supported_claims (list of strings)
- unsupported_claims (list of strings)
- reasoning (string explaining your evaluation)"""

        try:
            # Get validation result from LLM
            validation_result = await self.llm_service.generate_json(
                prompt=user_prompt,
                system_message=system_prompt,
                max_tokens=1500,
                temperature=0.1
            )
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            # Ensure all expected fields are present
            expected_fields = [
                "factuality_score", "relevance_score", "completeness_score", 
                "hallucination_score", "overall_score", "supported_claims",
                "unsupported_claims", "reasoning"
            ]
            
            for field in expected_fields:
                if field not in validation_result:
                    validation_result[field] = 0.0 if "score" in field else []
            
            # Add execution time
            validation_result["execution_time"] = execution_time
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Error in {self.name}: {str(e)}")
            return {
                "factuality_score": 0.0,
                "relevance_score": 0.0,
                "completeness_score": 0.0,
                "hallucination_score": 0.0,
                "overall_score": 0.0,
                "supported_claims": [],
                "unsupported_claims": [f"Error evaluating answer: {str(e)}"],
                "reasoning": f"Error during validation: {str(e)}",
                "error": str(e),
                "execution_time": time.time() - start_time
            }
    
    async def post_process(self, process_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Post-process the validation result.
        
        Args:
            process_output: Dictionary containing agent's output
            
        Returns:
            Dict: Post-processed results suitable for client consumption
        """
        result = process_output.copy()
        
        # Add verdict for easier interpretation
        if "overall_score" in result:
            if result["overall_score"] >= 8.0:
                result["verdict"] = "HIGHLY RELIABLE"
            elif result["overall_score"] >= 6.0:
                result["verdict"] = "MOSTLY RELIABLE"
            elif result["overall_score"] >= 4.0:
                result["verdict"] = "PARTIALLY RELIABLE"
            else:
                result["verdict"] = "UNRELIABLE"
        
        # Add more user-friendly summary
        if "reasoning" in result:
            summary_lines = []
            
            if "factuality_score" in result:
                factuality = result["factuality_score"]
                if factuality >= 8:
                    summary_lines.append("✅ The answer is factually accurate based on the provided sources.")
                elif factuality >= 5:
                    summary_lines.append("⚠️ The answer contains some factual information but may have minor inaccuracies.")
                else:
                    summary_lines.append("❌ The answer contains significant factual errors or unsupported claims.")
            
            if "hallucination_score" in result:
                hallucination = result["hallucination_score"]
                if hallucination >= 8:
                    summary_lines.append("✅ No significant hallucinations detected.")
                elif hallucination >= 5:
                    summary_lines.append("⚠️ The answer may contain some unsupported claims.")
                else:
                    summary_lines.append("❌ The answer contains multiple hallucinations not supported by sources.")
            
            if "unsupported_claims" in result and result["unsupported_claims"]:
                if len(result["unsupported_claims"]) == 1:
                    summary_lines.append(f"❗ Unsupported claim detected: {result['unsupported_claims'][0]}")
                else:
                    summary_lines.append(f"❗ {len(result['unsupported_claims'])} unsupported claims detected.")
            
            result["summary"] = "\n".join(summary_lines)
        
        return result


# Register the agent in the factory
if __name__ != "__main__":
    from app.agents.factory import AgentFactory
    AgentFactory.register("AnswerValidatorAgent", AnswerValidatorAgent)