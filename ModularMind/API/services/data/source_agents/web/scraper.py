"""
Web scraping source agents.
"""

import logging
import hashlib
import time
from typing import Dict, List, Any, Optional, Union, Tuple
from urllib.parse import urlparse

from ..base import BaseSourceAgent, Document, ExtractResult, SourceAgentError

logger = logging.getLogger(__name__)

class WebScraperAgent(BaseSourceAgent):
    """Source agent for web scraping"""
    
    def initialize(self) -> bool:
        """
        Initialize web scraper
        
        Returns:
            bool: True if initialized successfully
        """
        try:
            # Check if required libraries are installed
            import requests
            from bs4 import BeautifulSoup
            
            # Validate URL
            url = self.config.connection.get("url")
            if not url:
                logger.error("URL is required")
                return False
            
            # Parse URL to validate format
            parsed_url = urlparse(url)
            if not parsed_url.scheme or not parsed_url.netloc:
                logger.error(f"Invalid URL format: {url}")
                return False
            
            self.initialized = True
            return True
        except ImportError:
            logger.error("Required libraries not installed. Install with: pip install requests beautifulsoup4")
            return False
        except Exception as e:
            logger.error(f"Error initializing web scraper: {str(e)}")
            return False
    
    def validate_config(self) -> Tuple[bool, Optional[str]]:
        """
        Validate configuration
        
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        # Check required connection parameters
        url = self.config.connection.get("url")
        if not url:
            return False, "URL is required"
        
        # Parse URL to validate format
        try:
            parsed_url = urlparse(url)
            if not parsed_url.scheme or not parsed_url.netloc:
                return False, f"Invalid URL format: {url}"
        except Exception:
            return False, f"Invalid URL: {url}"
        
        return True, None
    
    def extract(self) -> ExtractResult:
        """
        Extract content from web page
        
        Returns:
            ExtractResult: Extraction result
        """
        if not self.initialized:
            if not self.initialize():
                return ExtractResult(
                    success=False,
                    error_message="Failed to initialize web scraper"
                )
        
        try:
            import requests
            from bs4 import BeautifulSoup
            
            # Get URL
            url = self.config.connection.get("url")
            
            # Get extraction options
            headers = self.config.options.get("headers", {})
            timeout = self.config.options.get("timeout", 30)
            extract_images = self.config.options.get("extract_images", False)
            extract_links = self.config.options.get("extract_links", True)
            extract_tables = self.config.options.get("extract_tables", True)
            extract_metadata = self.config.options.get("extract_metadata", True)
            
            # Set default user agent if not provided
            if "User-Agent" not in headers:
                headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            
            # Track statistics
            stats = {
                "start_time": time.time()
            }
            
            # Fetch web page
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Extract metadata
            metadata = {
                "url": url,
                "status_code": response.status_code,
                "content_type": response.headers.get("Content-Type", "")
            }
            
            if extract_metadata:
                # Extract page title
                title = soup.title.string if soup.title else ""
                metadata["title"] = title
                
                # Extract meta tags
                meta_tags = {}
                for meta in soup.find_all("meta"):
                    name = meta.get("name", meta.get("property", ""))
                    content = meta.get("content", "")