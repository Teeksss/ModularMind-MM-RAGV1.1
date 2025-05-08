"""
Document file source agents.
"""

import os
import hashlib
import logging
from typing import Dict, List, Any, Optional, Union, Tuple
import time

from ..base import BaseSourceAgent, Document, ExtractResult, SourceAgentError

logger = logging.getLogger(__name__)

class PDFSourceAgent(BaseSourceAgent):
    """Source agent for PDF files"""
    
    def initialize(self) -> bool:
        """
        Initialize PDF agent
        
        Returns:
            bool: True if initialized successfully
        """
        try:
            # Check if required libraries are installed
            import PyPDF2
            
            # Validate path
            file_path = self.config.connection.get("path")
            if not file_path or not os.path.exists(file_path):
                logger.error(f"PDF file not found: {file_path}")
                return False
            
            self.initialized = True
            return True
        except ImportError:
            logger.error("PyPDF2 not installed. Install with: pip install PyPDF2")
            return False
        except Exception as e:
            logger.error(f"Error initializing PDF agent: {str(e)}")
            return False
    
    def validate_config(self) -> Tuple[bool, Optional[str]]:
        """
        Validate configuration
        
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        # Check required connection parameters
        file_path = self.config.connection.get("path")
        if not file_path:
            return False, "File path is required"
        
        # Check if file exists
        if not os.path.exists(file_path):
            return False, f"File not found: {file_path}"
        
        # Check if file is a PDF
        if not file_path.lower().endswith(".pdf"):
            return False, f"File is not a PDF: {file_path}"
        
        return True, None
    
    def extract(self) -> ExtractResult:
        """
        Extract text from PDF file
        
        Returns:
            ExtractResult: Extraction result
        """
        if not self.initialized:
            if not self.initialize():
                return ExtractResult(
                    success=False,
                    error_message="Failed to initialize PDF agent"
                )
        
        try:
            import PyPDF2
            
            # Get file path
            file_path = self.config.connection.get("path")
            
            # Get extraction options
            extract_by_page = self.config.options.get("extract_by_page", True)
            extract_metadata = self.config.options.get("extract_metadata", True)
            page_limit = self.config.options.get("page_limit", None)
            min_page_length = self.config.options.get("min_page_length", 50)
            
            # Track statistics
            stats = {
                "total_pages": 0,
                "extracted_pages": 0,
                "total_chars": 0,
                "start_time": time.time()
            }
            
            # Extract PDF
            documents = []
            
            with open(file_path, "rb") as file:
                # Open PDF file
                pdf = PyPDF2.PdfReader(file)
                
                # Get total pages
                total_pages = len(pdf.pages)
                stats["total_pages"] = total_pages
                
                # Extract file-level metadata
                file_metadata = {}
                
                if extract_metadata:
                    # Extract PDF metadata
                    if pdf.metadata:
                        for key, value in pdf.metadata.items():
                            # Clean up key name (remove leading '/')
                            clean_key = key[1:] if key.startswith("/") else key
                            file_metadata[clean_key] = str(value)
                
                # Add file information to metadata
                file_info = {
                    "filename": os.path.basename(file_path),
                    "filesize": os.path.getsize(file_path),
                    "filetype": "application/pdf",
                    "total_pages": total_pages
                }
                file_metadata.update(file_info)
                
                # Extract by page or whole document
                if extract_by_page:
                    # Determine page limit
                    pages_to_extract = total_pages
                    if page_limit is not None and page_limit > 0:
                        pages_to_extract = min(total_pages, page_limit)
                    
                    # Extract each page
                    for page_num in range(pages_to_extract):
                        try:
                            # Extract page
                            page = pdf.pages[page_num]
                            page_text = page.extract_text()
                            
                            # Skip empty or very short pages
                            if not page_text or len(page_text) < min_page_length:
                                continue
                            
                            # Create page metadata
                            page_metadata = {
                                "page_number": page_num + 1,
                                "page_index": page_num
                            }
                            page_metadata.update(file_metadata)
                            
                            # Generate base ID for the page
                            file_hash = hashlib.md5(file_path.encode()).hexdigest()[:8]
                            base_id = f"{file_hash}-page-{page_num+1}"
                            
                            # Create document
                            document = self.create_document(
                                content=page_text,
                                metadata=page_metadata,
                                base_id=base_id
                            )
                            
                            documents.append(document)
                            stats["extracted_pages"] += 1
                            stats["total_chars"] += len(page_text)
                            
                        except Exception as page_error:
                            logger.warning(f"Error extracting page {page_num+1}: {str(page_error)}")
                else:
                    # Extract entire document
                    full_text = ""
                    for page_num in range(total_pages):
                        try:
                            page = pdf.pages[page_num]
                            page_text = page.extract_text()
                            full_text += page_text + "\n\n"
                        except Exception as page_error:
                            logger.warning(f"Error extracting page {page_num+1}: {str(page_error)}")
                    
                    # Skip if no text extracted
                    if full_text.strip():
                        # Generate base ID for the document
                        file_hash = hashlib.md5(file_path.encode()).hexdigest()[:8]
                        base_id = f"{file_hash}-full"
                        
                        # Create document
                        document = self.create_document(
                            content=full_text,
                            metadata=file_metadata,
                            base_id=base_id
                        )
                        
                        documents.append(document)
                        stats["extracted_pages"] = total_pages
                        stats["total_chars"] = len(full_text)
            
            # Calculate stats
            stats["elapsed_time"] = time.time() - stats["start_time"]
            
            return ExtractResult(
                success=True,
                documents=documents,
                stats=stats
            )
            
        except Exception as e:
            error_message = f"Error extracting PDF: {str(e)}"
            logger.error(error_message)
            return ExtractResult(
                success=False,
                error_message=error_message
            )

class DocxSourceAgent(BaseSourceAgent):
    """Source agent for Microsoft Word (DOCX) files"""
    
    def initialize(self) -> bool:
        """
        Initialize DOCX agent
        
        Returns:
            bool: True if initialized successfully
        """
        try:
            # Check if required libraries are installed
            import docx2txt
            
            # Validate path
            file_path = self.config.connection.get("path")
            if not file_path or not os.path.exists(file_path):
                logger.error(f"DOCX file not found: {file_path}")
                return False
            
            self.initialized = True
            return True
        except ImportError:
            logger.error("docx2txt not installed. Install with: pip install docx2txt")
            return False
        except Exception as e:
            logger.error(f"Error initializing DOCX agent: {str(e)}")
            return False
    
    def validate_config(self) -> Tuple[bool, Optional[str]]:
        """
        Validate configuration
        
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        # Check required connection parameters
        file_path = self.config.connection.get("path")
        if not file_path:
            return False, "File path is required"
        
        # Check if file exists
        if not os.path.exists(file_path):
            return False, f"File not found: {file_path}"
        
        # Check if file is a DOCX
        if not file_path.lower().endswith(".docx"):
            return False, f"File is not a DOCX: {file_path}"
        
        return True, None
    
    def extract(self) -> ExtractResult:
        """
        Extract text from DOCX file
        
        Returns:
            ExtractResult: Extraction result
        """
        if not self.initialized:
            if not self.initialize():
                return ExtractResult(
                    success=False,
                    error_message="Failed to initialize DOCX agent"
                )
        
        try:
            import docx2txt
            
            # Get file path
            file_path = self.config.connection.get("path")
            
            # Track statistics
            stats = {
                "start_time": time.time()
            }
            
            # Extract text from DOCX
            text = docx2txt.process(file_path)
            
            # Get file metadata
            file_metadata = {
                "filename": os.path.basename(file_path),
                "filesize": os.path.getsize(file_path),
                "filetype": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            }
            
            # Generate base ID
            file_hash = hashlib.md5(file_path.encode()).hexdigest()[:8]
            base_id = f"{file_hash}-docx"
            
            # Create document
            document = self.create_document(
                content=text,
                metadata=file_metadata,
                base_id=base_id
            )
            
            # Calculate stats
            stats["total_chars"] = len(text)
            stats["elapsed_time"] = time.time() - stats["start_time"]
            
            return ExtractResult(
                success=True,
                documents=[document],
                stats=stats
            )
            
        except Exception as e:
            error_message = f"Error extracting DOCX: {str(e)}"
            logger.error(error_message)
            return ExtractResult(
                success=False,
                error_message=error_message
            )