from typing import Dict, Any, List, Optional, BinaryIO, Union
import logging
import base64
import io
import os
import tempfile
import time
import uuid
from pathlib import Path

from app.agents.base import BaseAgent
from app.services.document_service import get_document_service
from app.core.settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Optional: Import OCR libraries if available
try:
    import pytesseract
    from PIL import Image
    from pdf2image import convert_from_path, convert_from_bytes
    DEPENDENCIES_AVAILABLE = True
except ImportError:
    logger.warning("OCR dependencies not available. Install with: pip install pytesseract Pillow pdf2image")
    DEPENDENCIES_AVAILABLE = False


class OCRReaderAgent(BaseAgent):
    """
    Agent for extracting text from images and scanned documents using OCR.
    
    Supports various input formats:
    - Individual images (PNG, JPG, TIFF)
    - Multi-page PDFs
    - Base64 encoded images
    """
    
    def __init__(self):
        self.description = "Extracts text from images and scanned documents using OCR"
        self.version = "1.1"
        self.document_service = get_document_service()
        super().__init__()
    
    def _load_resources(self):
        """Load resources needed for OCR processing."""
        if not DEPENDENCIES_AVAILABLE:
            return
        
        # Configure pytesseract path if set in settings
        if hasattr(settings, 'ocr') and hasattr(settings.ocr, 'tesseract_path'):
            pytesseract.pytesseract.tesseract_cmd = settings.ocr.tesseract_path
        
        # Supported image formats
        self.supported_image_formats = {'.png', '.jpg', '.jpeg', '.tiff', '.tif', '.bmp', '.gif'}
        
        # Language mapping for OCR
        self.language_mapping = {
            'en': 'eng',
            'tr': 'tur',
            'de': 'deu',
            'fr': 'fra',
            'es': 'spa',
            'it': 'ita',
            'pt': 'por',
            'ru': 'rus',
            'ar': 'ara',
            'zh': 'chi_sim',
            'ja': 'jpn',
            'ko': 'kor'
        }
    
    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate that input data contains the required fields."""
        if not DEPENDENCIES_AVAILABLE:
            logger.error("Required dependencies not available for OCRReaderAgent")
            return False
        
        # Check if any of the valid input types are provided
        if not any(key in input_data for key in ['file_path', 'file_bytes', 'base64_image', 'image_url']):
            logger.warning("Missing required input: file_path, file_bytes, base64_image, or image_url")
            return False
        
        return True
    
    async def pre_process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare the input data for processing."""
        processed_data = input_data.copy()
        
        # Set default OCR language
        if 'language' not in processed_data:
            processed_data['language'] = 'en'
        
        # Map language to tesseract format
        lang_code = processed_data['language']
        processed_data['tesseract_lang'] = self.language_mapping.get(lang_code, 'eng')
        
        # Set default OCR options
        if 'ocr_config' not in processed_data:
            processed_data['ocr_config'] = {}
        
        # Set default DPI for PDF conversion
        if 'dpi' not in processed_data['ocr_config']:
            processed_data['ocr_config']['dpi'] = 300
        
        # Set default preprocessing settings
        if 'preprocessing' not in processed_data['ocr_config']:
            processed_data['ocr_config']['preprocessing'] = True
        
        return processed_data
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract text from images or scanned documents using OCR.
        
        Args:
            input_data: Dict containing one of:
                - file_path: Path to local image or PDF file
                - file_bytes: Binary data of image or PDF
                - base64_image: Base64 encoded image data
                - image_url: URL to an image (will be downloaded)
                
                Options:
                - language: Language code for OCR (default: 'en')
                - ocr_config: Additional OCR configuration
                - create_document: Whether to create a document (default: False)
                
        Returns:
            Dict with extracted text and metadata
        """
        # Get OCR language and config
        tesseract_lang = input_data['tesseract_lang']
        ocr_config = input_data['ocr_config']
        
        # Track processing time
        start_time = time.time()
        
        # Process based on input type
        if 'file_path' in input_data:
            text, pages, metadata = await self._process_file_path(
                input_data['file_path'], 
                tesseract_lang, 
                ocr_config
            )
        
        elif 'file_bytes' in input_data:
            text, pages, metadata = await self._process_file_bytes(
                input_data['file_bytes'], 
                tesseract_lang, 
                ocr_config
            )
        
        elif 'base64_image' in input_data:
            # Decode base64 to bytes
            file_bytes = base64.b64decode(input_data['base64_image'])
            text, pages, metadata = await self._process_file_bytes(
                file_bytes, 
                tesseract_lang, 
                ocr_config
            )
        
        elif 'image_url' in input_data:
            # Download image
            image_bytes = await self._download_image(input_data['image_url'])
            text, pages, metadata = await self._process_file_bytes(
                image_bytes, 
                tesseract_lang, 
                ocr_config
            )
        
        else:
            # This should not happen due to validation
            return {"error": "No valid input provided"}
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Create document if requested
        document_id = None
        if input_data.get('create_document', False):
            document_id = await self._create_document(text, metadata, input_data)
        
        # Return results
        result = {
            "text": text,
            "page_count": len(pages),
            "pages": pages,
            "metadata": metadata,
            "processing_time": processing_time,
            "language": input_data['language']
        }
        
        if document_id:
            result["document_id"] = document_id
        
        return result
    
    async def _process_file_path(self, file_path: str, lang: str, config: Dict[str, Any]) -> tuple:
        """Process a file from local path."""
        file_path = Path(file_path)
        file_ext = file_path.suffix.lower()
        
        # Detect if file is a PDF
        if file_ext == '.pdf':
            return await self._process_pdf_file(file_path, lang, config)
        
        # Process as a single image
        elif file_ext in self.supported_image_formats:
            return await self._process_image_file(file_path, lang, config)
        
        else:
            raise ValueError(f"Unsupported file format: {file_ext}")
    
    async def _process_file_bytes(self, file_bytes: bytes, lang: str, config: Dict[str, Any]) -> tuple:
        """Process a file from binary data."""
        # Try to determine file type
        if self._is_pdf(file_bytes):
            # Process as PDF
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                temp_file.write(file_bytes)
                temp_path = temp_file.name
            
            try:
                return await self._process_pdf_file(temp_path, lang, config)
            finally:
                os.unlink(temp_path)
        else:
            # Process as image
            image = Image.open(io.BytesIO(file_bytes))
            return await self._process_image(image, lang, config)
    
    async def _process_pdf_file(self, pdf_path, lang: str, config: Dict[str, Any]) -> tuple:
        """Process a PDF file and extract text from all pages."""
        # Convert PDF to images
        dpi = config.get('dpi', 300)
        try:
            images = convert_from_path(pdf_path, dpi=dpi)
        except Exception as e:
            logger.error(f"Error converting PDF to images: {str(e)}")
            raise
        
        # Process each page
        all_pages = []
        all_text = ""
        
        for i, image in enumerate(images):
            page_text, _, _ = await self._process_image(image, lang, config)
            all_text += f"\n\n--- Page {i+1} ---\n\n" + page_text
            all_pages.append({
                "page_num": i + 1,
                "text": page_text
            })
        
        # Metadata
        metadata = {
            "source_type": "pdf",
            "page_count": len(images),
            "dpi": dpi,
            "ocr_language": lang
        }
        
        return all_text, all_pages, metadata
    
    async def _process_image_file(self, image_path, lang: str, config: Dict[str, Any]) -> tuple:
        """Process an image file."""
        image = Image.open(image_path)
        return await self._process_image(image, lang, config)
    
    async def _process_image(self, image, lang: str, config: Dict[str, Any]) -> tuple:
        """Process a single image with OCR."""
        # Apply preprocessing if enabled
        if config.get('preprocessing', True):
            image = self._preprocess_image(image)
        
        # Extract text using OCR
        try:
            ocr_text = pytesseract.image_to_string(image, lang=lang)
        except Exception as e:
            logger.error(f"OCR error: {str(e)}")
            raise
        
        # Metadata
        metadata = {
            "source_type": "image",
            "image_size": f"{image.width}x{image.height}",
            "image_format": image.format,
            "ocr_language": lang
        }
        
        # Single page result
        pages = [{
            "page_num": 1,
            "text": ocr_text
        }]
        
        return ocr_text, pages, metadata
    
    async def _download_image(self, url: str) -> bytes:
        """Download an image from URL."""
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.content
    
    def _preprocess_image(self, image):
        """Apply preprocessing to improve OCR quality."""
        try:
            # Convert to grayscale
            if image.mode != 'L':
                image = image.convert('L')
            
            # You can add more preprocessing here:
            # - Thresholding
            # - Noise reduction
            # - Deskewing
            # - Contrast enhancement
            
            return image
        except Exception as e:
            logger.warning(f"Image preprocessing failed: {str(e)}")
            return image
    
    def _is_pdf(self, data: bytes) -> bool:
        """Check if the binary data is a PDF file."""
        return data[:4] == b'%PDF'
    
    async def _create_document(self, text: str, metadata: Dict, input_data: Dict) -> Optional[str]:
        """Create a document from extracted text."""
        try:
            # Determine title based on input type
            title = "OCR Extracted Document"
            if 'file_path' in input_data:
                title = f"OCR: {os.path.basename(input_data['file_path'])}"
            
            # Prepare document data
            doc_data = {
                "title": title,
                "content": text,
                "content_type": "text/plain",
                "source": "ocr-extraction",
                "language": input_data['language'],
                "metadata": {
                    "ocr_extracted": True,
                    "extraction_date": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
                    **metadata
                }
            }
            
            # Create document
            document = await self.document_service.create_document(doc_data)
            return document.id
            
        except Exception as e:
            logger.error(f"Error creating document: {str(e)}")
            return None
    
    async def post_process(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Clean up and finalize results."""
        # Calculate text statistics
        if "text" in result:
            text = result["text"]
            word_count = len(text.split())
            char_count = len(text)
            
            result["text_stats"] = {
                "word_count": word_count,
                "character_count": char_count,
                "estimated_quality": self._estimate_ocr_quality(text)
            }
        
        return result
    
    def _estimate_ocr_quality(self, text: str) -> Dict[str, Any]:
        """Estimate the quality of OCR results."""
        # This is a simplistic quality estimate; a real implementation would be more sophisticated
        if not text:
            return {"score": 0, "confidence": "poor"}
        
        # Check for common OCR errors
        error_chars = sum(1 for c in text if c in '¦|lI1' or ord(c) > 127)
        error_ratio = error_chars / len(text) if text else 1
        
        # Count words with likely OCR errors
        words = text.split()
        suspicious_words = sum(1 for word in words if self._is_suspicious_word(word))
        suspicious_ratio = suspicious_words / len(words) if words else 1
        
        # Calculate overall quality score
        quality_score = 1.0 - (error_ratio * 0.5 + suspicious_ratio * 0.5)
        quality_score = max(0, min(1, quality_score))
        
        # Map score to confidence level
        confidence = "excellent"
        if quality_score < 0.6:
            confidence = "poor"
        elif quality_score < 0.75:
            confidence = "fair"
        elif quality_score < 0.9:
            confidence = "good"
        
        return {
            "score": round(quality_score, 2),
            "confidence": confidence,
            "error_chars_ratio": round(error_ratio, 2),
            "suspicious_words_ratio": round(suspicious_ratio, 2)
        }
    
    def _is_suspicious_word(self, word: str) -> bool:
        """Check if a word looks like it contains OCR errors."""
        # Check for words with unusual character combinations
        if len(word) <= 2:
            return False
        
        # Suspect words with unusual character patterns
        suspicious_patterns = [
            r'[a-z][A-Z][a-z]',  # Mixed case in middle
            r'[0-9][a-zA-Z][0-9]',  # Digit-letter-digit
            r'[a-zA-Z][0-9][a-zA-Z]',  # Letter-digit-letter
            r'[^a-zA-Z0-9.,;:\'"-\s]{2}',  # Two special chars in a row
        ]
        
        return any(re.search(pattern, word) for pattern in suspicious_patterns)