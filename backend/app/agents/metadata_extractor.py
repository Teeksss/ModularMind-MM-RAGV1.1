from typing import Dict, Any, List, Optional, Tuple
import logging
import re
from datetime import datetime
import dateutil.parser
from langdetect import detect, LangDetectException

from app.agents.base import BaseAgent
from app.services.llm_service import get_llm_service
from app.core.settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class MetadataExtractorAgent(BaseAgent):
    """
    Agent for extracting metadata from documents.
    
    Extracts information such as:
    - Document language
    - Creation/modification dates
    - Author information
    - Document type and format
    - Keywords and topics
    """
    
    def __init__(self):
        self.description = "Extracts metadata from documents"
        self.version = "1.1"
        self.llm_service = get_llm_service()
        super().__init__()
    
    def _load_resources(self):
        """Load resources needed for metadata extraction."""
        # Define extraction prompts
        self.general_metadata_prompt = """
        Extract the following metadata from the document:
        - title (the document's title or a generated one if none exists)
        - author (name of the author if present)
        - date (publication or creation date if present, in YYYY-MM-DD format)
        - document_type (e.g., article, report, policy, manual, etc.)
        - summary (a brief 1-2 sentence summary)
        - keywords (5-10 key topics or terms)
        
        Document:
        {document_content}
        
        Return the extracted metadata as a JSON object with the fields above.
        If you can't extract a particular field with confidence, use null.
        """
        
        # Regular expressions for direct extraction
        self.date_pattern = re.compile(r'\b(\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4}|\d{4}[./\-]\d{1,2}[./\-]\d{1,2})\b')
        self.email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    
    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate that input data contains the required fields."""
        if 'document_content' not in input_data or not input_data['document_content']:
            logger.warning("Missing document_content in input data")
            return False
        return True
    
    async def pre_process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare the document content for metadata extraction."""
        processed_data = input_data.copy()
        
        # Limit document content to a reasonable size for metadata extraction
        if len(processed_data['document_content']) > 10000:
            processed_data['document_content'] = processed_data['document_content'][:10000]
            logger.info("Document content truncated for metadata extraction")
        
        return processed_data
    
    def _detect_language(self, text: str) -> str:
        """Detect the language of the document."""
        try:
            # Use at least 100 characters for detection, if available
            sample = text[:min(1000, len(text))]
            if len(sample) < 10:  # Too short for reliable detection
                return settings.multilingual.default_language
                
            lang = detect(sample)
            return lang
        except LangDetectException:
            logger.warning("Could not detect language, using default")
            return settings.multilingual.default_language
    
    def _extract_dates(self, text: str) -> List[str]:
        """Extract dates from text using regex."""
        dates = self.date_pattern.findall(text)
        
        # Convert to consistent format (YYYY-MM-DD)
        formatted_dates = []
        for date_str in dates:
            try:
                # Parse the date with dateutil
                date_obj = dateutil.parser.parse(date_str, fuzzy=True)
                # Format as YYYY-MM-DD
                formatted_date = date_obj.strftime("%Y-%m-%d")
                formatted_dates.append(formatted_date)
            except (ValueError, OverflowError):
                # Skip dates that can't be parsed
                continue
        
        return formatted_dates
    
    def _extract_emails(self, text: str) -> List[str]:
        """Extract email addresses from text."""
        return self.email_pattern.findall(text)
    
    def _extract_content_type(self, content_type: str, filename: Optional[str] = None) -> Tuple[str, str]:
        """
        Extract document and content type from content_type and filename.
        
        Returns:
            Tuple of (document_type, content_format)
        """
        document_type = "unknown"
        content_format = content_type or "text/plain"
        
        # Extract from content_type
        if content_type:
            if 'pdf' in content_type:
                document_type = "document"
                content_format = "application/pdf"
            elif 'word' in content_type or 'docx' in content_type:
                document_type = "document"
                content_format = "application/docx"
            elif 'html' in content_type:
                document_type = "webpage"
                content_format = "text/html"
            elif 'text' in content_type:
                document_type = "text"
                content_format = "text/plain"
            elif 'json' in content_type:
                document_type = "data"
                content_format = "application/json"
            elif 'csv' in content_type:
                document_type = "data"
                content_format = "text/csv"
        
        # Extract from filename if available
        if filename:
            filename = filename.lower()
            if filename.endswith('.pdf'):
                document_type = "document"
                content_format = "application/pdf"
            elif filename.endswith(('.doc', '.docx')):
                document_type = "document"
                content_format = "application/docx"
            elif filename.endswith(('.html', '.htm')):
                document_type = "webpage"
                content_format = "text/html"
            elif filename.endswith('.txt'):
                document_type = "text"
                content_format = "text/plain"
            elif filename.endswith('.json'):
                document_type = "data"
                content_format = "application/json"
            elif filename.endswith('.csv'):
                document_type = "data"
                content_format = "text/csv"
            elif filename.endswith(('.jpg', '.jpeg', '.png', '.gif')):
                document_type = "image"
                content_format = f"image/{filename.split('.')[-1]}"
        
        return document_type, content_format
    
    async def _extract_llm_metadata(self, text: str) -> Dict[str, Any]:
        """Extract metadata using LLM."""
        prompt = self.general_metadata_prompt.format(document_content=text)
        
        try:
            metadata = await self.llm_service.generate_json(
                prompt=prompt,
                temperature=0.0
            )
            
            if not isinstance(metadata, dict):
                logger.warning(f"Unexpected format from LLM: {type(metadata)}")
                return {}
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error extracting metadata with LLM: {str(e)}")
            return {}
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract metadata from document content.
        
        Args:
            input_data: Dict containing 'document_content' and optional metadata
            
        Returns:
            Dict with extracted metadata
        """
        document_content = input_data['document_content']
        
        # Extract basic metadata without LLM
        language = self._detect_language(document_content)
        dates = self._extract_dates(document_content)
        emails = self._extract_emails(document_content)
        
        # Get content_type and filename if provided
        content_type = input_data.get('content_type', 'text/plain')
        filename = input_data.get('filename')
        
        # Extract document type and format
        document_type, content_format = self._extract_content_type(content_type, filename)
        
        # Get document size in bytes
        document_size = len(document_content.encode('utf-8'))
        
        # Extract LLM-based metadata
        llm_metadata = await self._extract_llm_metadata(document_content)
        
        # Combine all metadata
        metadata = {
            "language": language,
            "document_type": llm_metadata.get("document_type", document_type),
            "content_format": content_format,
            "size_bytes": document_size,
            "extracted_dates": dates,
            "extracted_emails": emails,
            "title": llm_metadata.get("title"),
            "author": llm_metadata.get("author"),
            "creation_date": llm_metadata.get("date"),
            "keywords": llm_metadata.get("keywords", []),
            "summary": llm_metadata.get("summary"),
            "original_filename": filename,
        }
        
        # Add additional metadata if provided in input
        for key, value in input_data.items():
            if key not in ['document_content', 'content_type', 'filename'] and key not in metadata:
                metadata[key] = value
        
        return {
            "metadata": metadata,
            "document_id": input_data.get("document_id", "unknown")
        }
    
    async def post_process(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Clean up metadata and ensure consistent format."""
        if "metadata" not in result:
            return result
        
        metadata = result["metadata"]
        
        # Clean up keywords if present
        if "keywords" in metadata and metadata["keywords"]:
            # If keywords is a string, convert to list
            if isinstance(metadata["keywords"], str):
                keywords = [k.strip() for k in metadata["keywords"].split(",")]
                metadata["keywords"] = keywords
            
            # Ensure all keywords are strings
            metadata["keywords"] = [str(k) for k in metadata["keywords"]]
        
        # Ensure dates are in YYYY-MM-DD format
        if "creation_date" in metadata and metadata["creation_date"]:
            try:
                date = dateutil.parser.parse(metadata["creation_date"], fuzzy=True)
                metadata["creation_date"] = date.strftime("%Y-%m-%d")
            except (ValueError, OverflowError, TypeError):
                # If date can't be parsed, use the first extracted date or None
                metadata["creation_date"] = metadata.get("extracted_dates", [None])[0]
        
        # Set sensible defaults for missing fields
        if not metadata.get("title"):
            # Generate a title from first 50 chars of content if no title found
            content = result.get("document_content", "")
            if isinstance(content, str) and content:
                content_sample = content[:50].strip()
                if len(content_sample) < 10:  # Too short for a meaningful title
                    metadata["title"] = "Untitled Document"
                else:
                    metadata["title"] = f"{content_sample}..."
            else:
                metadata["title"] = "Untitled Document"
        
        return result