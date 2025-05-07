from typing import Dict, Any, List, Optional, Set
import logging
import re
import json
import asyncio
import time
from urllib.parse import urlparse, urljoin
from pydantic import BaseModel, Field

from app.agents.base import BaseAgent
from app.services.llm_service import get_llm_service
from app.services.document_service import get_document_service
from app.core.settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Optional: Import these libraries if they are available
try:
    import httpx
    from bs4 import BeautifulSoup
    from readability import Document as ReadabilityDocument
    DEPENDENCIES_AVAILABLE = True
except ImportError:
    logger.warning("Web scraper dependencies not available. Install with: pip install httpx beautifulsoup4 readability-lxml")
    DEPENDENCIES_AVAILABLE = False


class WebPage(BaseModel):
    """Model for storing web page data."""
    url: str
    title: str
    content: str
    html: str
    links: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WebScraperConfig(BaseModel):
    """Configuration for the web scraper agent."""
    max_depth: int = 1
    max_pages: int = 10
    follow_links: bool = True
    include_patterns: List[str] = Field(default_factory=list)
    exclude_patterns: List[str] = Field(default_factory=list)
    headers: Dict[str, str] = Field(default_factory=dict)
    timeout: int = 30


class WebScraperAgent(BaseAgent):
    """
    Agent for scraping web content.
    
    Extracts text, metadata, and links from web pages.
    Can optionally follow links to scrape related pages.
    """
    
    def __init__(self):
        self.description = "Scrapes content from web pages"
        self.version = "1.1"
        self.llm_service = get_llm_service()
        self.document_service = get_document_service()
        super().__init__()
    
    def _load_resources(self):
        """Load resources needed for web scraping."""
        # Set default headers for requests
        self.default_headers = {
            "User-Agent": "ModularMind/1.1 (compatible; +https://modularmind.com/bot)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0"
        }
        
        # Metadata extraction prompt
        self.metadata_extraction_prompt = """
        Extract key metadata from the following web page content.
        
        Title: {title}
        URL: {url}
        
        Content excerpt:
        {content_excerpt}
        
        Return your response as a JSON object with the following fields:
        1. "author": The author of the page (if available)
        2. "published_date": The publication date (if available)
        3. "main_topic": The main topic or category
        4. "keywords": An array of relevant keywords
        5. "summary": A brief summary of the content
        
        Only include the JSON object, nothing else.
        """
    
    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate that input data contains the required fields."""
        if not DEPENDENCIES_AVAILABLE:
            logger.error("Required dependencies not available for WebScraperAgent")
            return False
        
        if 'url' not in input_data:
            logger.warning("Missing url in input data")
            return False
        
        # Validate URL format
        try:
            result = urlparse(input_data['url'])
            if not all([result.scheme, result.netloc]):
                logger.warning(f"Invalid URL format: {input_data['url']}")
                return False
        except Exception as e:
            logger.warning(f"Error parsing URL: {str(e)}")
            return False
        
        return True
    
    async def pre_process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare the input data for processing."""
        processed_data = input_data.copy()
        
        # Create config from input or use defaults
        config_data = processed_data.get('config', {})
        processed_data['config'] = WebScraperConfig(**config_data)
        
        # Merge user headers with default headers
        user_headers = processed_data['config'].headers
        processed_data['config'].headers = {**self.default_headers, **user_headers}
        
        # Initialize tracking sets for visited and queued URLs
        processed_data['visited_urls'] = set()
        processed_data['queued_urls'] = set([processed_data['url']])
        
        return processed_data
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Scrape web content from the provided URL.
        
        Args:
            input_data: Dict containing:
                - url: The starting URL to scrape
                - config: Optional scraper configuration
                
        Returns:
            Dict with scraped pages and metadata
        """
        start_url = input_data['url']
        config = input_data['config']
        visited_urls = input_data['visited_urls']
        queued_urls = input_data['queued_urls']
        
        # Store all scraped pages
        scraped_pages = []
        
        # Create an async client
        async with httpx.AsyncClient(
            timeout=config.timeout,
            follow_redirects=True,
            headers=config.headers
        ) as client:
            # Start with the initial URL
            current_depth = 0
            current_urls = [start_url]
            
            # Process URLs level by level until max depth is reached
            while current_urls and current_depth <= config.max_depth and len(scraped_pages) < config.max_pages:
                next_urls = []
                
                # Process URLs at current depth
                tasks = [self._scrape_url(client, url, config) for url in current_urls]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for url, result in zip(current_urls, results):
                    # Mark URL as visited
                    visited_urls.add(url)
                    
                    # Handle exceptions
                    if isinstance(result, Exception):
                        logger.warning(f"Error scraping {url}: {str(result)}")
                        continue
                    
                    # Add scraped page to results
                    scraped_pages.append(result)
                    
                    # Collect links for next level
                    if config.follow_links and current_depth < config.max_depth:
                        for link in result.links:
                            absolute_link = urljoin(url, link)
                            
                            # Skip if already visited or queued
                            if absolute_link in visited_urls or absolute_link in queued_urls:
                                continue
                            
                            # Apply include/exclude filters
                            if (not config.include_patterns or 
                                any(re.search(pattern, absolute_link) for pattern in config.include_patterns)):
                                
                                if (not config.exclude_patterns or 
                                    not any(re.search(pattern, absolute_link) for pattern in config.exclude_patterns)):
                                    
                                    next_urls.append(absolute_link)
                                    queued_urls.add(absolute_link)
                    
                    # Stop if we've reached the maximum pages
                    if len(scraped_pages) >= config.max_pages:
                        break
                
                # Move to next depth level
                current_urls = next_urls
                current_depth += 1
        
        # Convert pages to dictionary format
        page_data = [page.dict() for page in scraped_pages]
        
        # Create documents if requested
        created_docs = []
        if input_data.get('create_documents', False):
            for page in scraped_pages:
                try:
                    doc_id = await self._create_document(page)
                    if doc_id:
                        created_docs.append(doc_id)
                except Exception as e:
                    logger.error(f"Error creating document for {page.url}: {str(e)}")
        
        # Return results
        return {
            "pages": page_data,
            "stats": {
                "total_pages": len(scraped_pages),
                "total_visited": len(visited_urls),
                "max_depth_reached": current_depth - 1
            },
            "created_documents": created_docs
        }
    
    async def _scrape_url(self, client, url: str, config: WebScraperConfig) -> WebPage:
        """Scrape a single URL and extract content."""
        logger.info(f"Scraping URL: {url}")
        
        # Fetch the page
        response = await client.get(url)
        response.raise_for_status()
        html = response.text
        
        # Parse with readability to extract main content
        readability_doc = ReadabilityDocument(html)
        title = readability_doc.title()
        content = readability_doc.summary()
        
        # Extract clean text from HTML
        soup = BeautifulSoup(content, 'html.parser')
        text_content = soup.get_text(separator='\n\n', strip=True)
        
        # Extract links
        links = []
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            if href and not href.startswith('#') and not href.startswith('javascript:'):
                links.append(href)
        
        # Extract metadata using LLM
        metadata = await self._extract_metadata(title, url, text_content[:1000])
        
        # Create WebPage object
        page = WebPage(
            url=url,
            title=title,
            content=text_content,
            html=html,
            links=links,
            metadata=metadata
        )
        
        return page
    
    async def _extract_metadata(self, title: str, url: str, content_excerpt: str) -> Dict[str, Any]:
        """Extract metadata from page content using LLM."""
        try:
            prompt = self.metadata_extraction_prompt.format(
                title=title,
                url=url,
                content_excerpt=content_excerpt
            )
            
            metadata = await self.llm_service.generate_json(
                prompt=prompt,
                temperature=0.2
            )
            
            if not isinstance(metadata, dict):
                return {}
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error extracting metadata: {str(e)}")
            return {}
    
    async def _create_document(self, page: WebPage) -> Optional[str]:
        """Create a document from the scraped page."""
        try:
            # Prepare document data
            doc_data = {
                "title": page.title,
                "content": page.content,
                "content_type": "text/html",
                "source": page.url,
                "language": "en",  # This could be detected
                "metadata": {
                    "source_url": page.url,
                    "scrape_date": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
                    "html_length": len(page.html),
                    **page.metadata
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
        # Limit HTML content size in results to avoid huge responses
        if "pages" in result:
            for page in result["pages"]:
                if len(page.get("html", "")) > 1000:
                    page["html"] = page["html"][:1000] + "... [truncated]"
        
        return result