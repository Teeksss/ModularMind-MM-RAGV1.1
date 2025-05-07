from typing import Dict, Any, List, Optional
import logging
import re
from langchain.text_splitter import RecursiveCharacterTextSplitter

from app.agents.base import BaseAgent
from app.services.llm_service import get_llm_service
from app.core.settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class SummarizationAgent(BaseAgent):
    """
    Agent for generating summaries of documents.
    
    Features:
    - Multi-level summarization for long documents
    - Section-based summarization for structured content
    - Abstract, executive, and detailed summary types
    - Multilingual support
    """
    
    def __init__(self):
        self.description = "Generates summaries for documents"
        self.version = "1.1"
        self.llm_service = get_llm_service()
        super().__init__()
    
    def _load_resources(self):
        """Load resources needed for summarization."""
        # Define summarization prompts for different scenarios
        self.short_summary_prompt = """
        Create a concise summary of the following document. 
        Focus on the key points, main arguments, and important conclusions.
        
        Document Content:
        {document_content}
        
        Summary:
        """
        
        self.executive_summary_prompt = """
        Create an executive summary of the following document.
        Focus on the most important information, key findings, main conclusions, 
        and any actionable recommendations.
        
        Document Content:
        {document_content}
        
        Executive Summary:
        """
        
        self.detailed_summary_prompt = """
        Create a detailed summary of the following document.
        Include the main points from each section, key findings, methodologies used,
        and important conclusions. Preserve the structure of the original document.
        
        Document Content:
        {document_content}
        
        Detailed Summary:
        """
        
        self.section_summary_prompt = """
        This is a section from a larger document. Create a concise summary of this section.
        
        Section Content:
        {section_content}
        
        Section Summary:
        """
        
        self.recursive_summary_prompt = """
        Below are summaries of different sections of a document. Create a cohesive overall
        summary that combines these section summaries into a unified summary.
        
        Section Summaries:
        {section_summaries}
        
        Overall Summary:
        """
        
        # Initialize text splitter for long documents
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=4000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    
    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate that input data contains the required fields."""
        if 'document_content' not in input_data or not input_data['document_content']:
            logger.warning("Missing document_content in input data")
            return False
        return True
    
    async def _identify_sections(self, text: str) -> List[Dict[str, Any]]:
        """
        Identify logical sections in a document based on headings.
        
        Args:
            text: Document text
            
        Returns:
            List of sections with title and content
        """
        # Simple section detection using heading patterns
        # This is a basic implementation - could be enhanced with ML
        heading_patterns = [
            r'^#{1,6}\s+(.+)$',  # Markdown headings
            r'^(\d+\.[\d\.]*)\s+(.+)$',  # Numbered headings like "1.2.3 Section Title"
            r'^([A-Z][A-Za-z\s]+)$',  # All caps or title case lines that might be headings
            r'^(Chapter|Section|Part)\s+\w+:?\s*(.+)$',  # Explicit section markers
        ]
        
        lines = text.split('\n')
        sections = []
        current_section = {"title": "Introduction", "content": ""}
        
        for line in lines:
            is_heading = False
            
            for pattern in heading_patterns:
                match = re.match(pattern, line.strip())
                if match:
                    # Save current section
                    if current_section["content"].strip():
                        sections.append(current_section.copy())
                    
                    # Start new section
                    if len(match.groups()) > 1:
                        title = " ".join(match.groups())
                    else:
                        title = match.group(1)
                        
                    current_section = {"title": title, "content": ""}
                    is_heading = True
                    break
            
            if not is_heading:
                current_section["content"] += line + "\n"
        
        # Add the last section
        if current_section["content"].strip():
            sections.append(current_section)
        
        # If no sections were found, treat the whole text as one section
        if not sections:
            sections = [{"title": "Document", "content": text}]
        
        return sections
    
    async def _summarize_text(self, text: str, prompt_template: str, max_length: int = 4000) -> str:
        """
        Summarize text using the LLM.
        
        Args:
            text: Text to summarize
            prompt_template: Prompt template to use
            max_length: Maximum length of text to summarize directly
            
        Returns:
            Summary text
        """
        # For short texts, summarize directly
        if len(text) <= max_length:
            prompt = prompt_template.format(document_content=text)
            return await self.llm_service.generate(prompt=prompt)
        
        # For longer texts, split and summarize recursively
        chunks = self.text_splitter.split_text(text)
        
        # Summarize each chunk
        chunk_summaries = []
        for chunk in chunks:
            prompt = self.section_summary_prompt.format(section_content=chunk)
            summary = await self.llm_service.generate(prompt=prompt)
            chunk_summaries.append(summary)
        
        # Combine chunk summaries
        combined_summaries = "\n\n".join(chunk_summaries)
        
        # If the combined summaries are still too long, summarize recursively
        if len(combined_summaries) > max_length:
            return await self._summarize_text(combined_summaries, self.recursive_summary_prompt)
        
        # Generate final summary from the combined chunk summaries
        prompt = self.recursive_summary_prompt.format(section_summaries=combined_summaries)
        return await self.llm_service.generate(prompt=prompt)
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a summary for the document.
        
        Args:
            input_data: Dict containing 'document_content' and optionally 'summary_type'
            
        Returns:
            Dict with generated summary and metadata
        """
        document_content = input_data['document_content']
        document_id = input_data.get('document_id', 'unknown')
        summary_type = input_data.get('summary_type', 'standard')  # standard, executive, detailed
        
        # Get language if provided, otherwise use default
        language = input_data.get('language', settings.multilingual.default_language)
        
        # Adjust summarization approach based on document length
        document_length = len(document_content)
        logger.info(f"Generating {summary_type} summary for document {document_id} ({document_length} chars)")
        
        # Select appropriate prompt based on summary type
        if summary_type == 'executive':
            prompt_template = self.executive_summary_prompt
        elif summary_type == 'detailed':
            prompt_template = self.detailed_summary_prompt
        else:  # standard
            prompt_template = self.short_summary_prompt
        
        # For detailed summaries of longer documents, use section-based approach
        if summary_type == 'detailed' and document_length > 5000:
            # Identify document sections
            sections = await self._identify_sections(document_content)
            
            # Summarize each section
            section_summaries = []
            for section in sections:
                section_title = section["title"]
                section_content = section["content"]
                
                # Skip very short sections
                if len(section_content.strip()) < 100:
                    continue
                
                prompt = self.section_summary_prompt.format(section_content=section_content)
                section_summary = await self.llm_service.generate(prompt=prompt)
                
                section_summaries.append(f"## {section_title}\n\n{section_summary}")
            
            # Combine section summaries
            detailed_summary = "\n\n".join(section_summaries)
            
            # Create a shorter overall summary
            combined_text = "\n\n".join([s["content"] for s in sections])
            overall_summary = await self._summarize_text(combined_text, self.short_summary_prompt)
            
            summary = {
                "overall": overall_summary,
                "detailed": detailed_summary,
                "sections": [s["title"] for s in sections]
            }
        else:
            # For shorter documents or non-detailed summaries, summarize directly
            summary_text = await self._summarize_text(document_content, prompt_template)
            summary = {"overall": summary_text}
        
        return {
            "summary": summary,
            "document_id": document_id,
            "summary_type": summary_type,
            "document_length": document_length,
            "language": language
        }
    
    async def post_process(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Clean up and format the summary."""
        # Ensure summary has proper formatting
        if "summary" in result and "overall" in result["summary"]:
            # Remove any extra whitespace and markdown artifacts
            result["summary"]["overall"] = result["summary"]["overall"].strip()
            
            # If detailed summary exists, clean it up too
            if "detailed" in result["summary"]:
                result["summary"]["detailed"] = result["summary"]["detailed"].strip()
        
        return result