from typing import Dict, Any, List, Optional, Union
import logging
import json
import time
import asyncio
import uuid
from pydantic import BaseModel, Field, validator

from app.agents.base import BaseAgent
from app.services.document_service import get_document_service
from app.core.settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Optional: Import httpx if available
try:
    import httpx
    DEPENDENCIES_AVAILABLE = True
except ImportError:
    logger.warning("API reader dependencies not available. Install with: pip install httpx")
    DEPENDENCIES_AVAILABLE = False


class APIEndpoint(BaseModel):
    """Model for API endpoint configuration."""
    url: str
    method: str = "GET"
    headers: Dict[str, str] = Field(default_factory=dict)
    params: Dict[str, Any] = Field(default_factory=dict)
    body: Optional[Dict[str, Any]] = None
    auth_type: Optional[str] = None  # "basic", "bearer", "api_key", "oauth2"
    auth_config: Dict[str, Any] = Field(default_factory=dict)
    pagination: Dict[str, Any] = Field(default_factory=dict)
    timeout: int = 30
    retry: int = 3
    content_path: Optional[str] = None  # JSONPath to extract content


class APIResponse(BaseModel):
    """Model for API response data."""
    url: str
    status_code: int
    response_time: float
    content_type: str
    data: Any
    headers: Dict[str, str]
    is_success: bool
    error_message: Optional[str] = None


class APIReaderAgent(BaseAgent):
    """
    Agent for reading data from external APIs.
    
    Fetches data from REST APIs and transforms it into documents.
    Supports various authentication methods, pagination, and data extraction.
    """
    
    def __init__(self):
        self.description = "Fetches and processes data from external APIs"
        self.version = "1.1"
        self.document_service = get_document_service()
        super().__init__()
    
    def _load_resources(self):
        """Load resources needed for API handling."""
        # Default headers for API requests
        self.default_headers = {
            "User-Agent": "ModularMind/1.1 (+https://modularmind.com/bot)",
            "Accept": "application/json"
        }
        
        # Define pagination strategies
        self.pagination_strategies = {
            "offset": self._paginate_with_offset,
            "page": self._paginate_with_page,
            "cursor": self._paginate_with_cursor,
            "link_header": self._paginate_with_link_header
        }
    
    async def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate that input data contains the required fields."""
        if not DEPENDENCIES_AVAILABLE:
            logger.error("Required dependencies not available for APIReaderAgent")
            return False
        
        if 'api_config' not in input_data and 'endpoints' not in input_data:
            logger.warning("Missing required input: api_config or endpoints")
            return False
        
        # If endpoints array is provided, validate each endpoint
        if 'endpoints' in input_data:
            if not isinstance(input_data['endpoints'], list) or not input_data['endpoints']:
                logger.warning("Endpoints must be a non-empty list")
                return False
        
        # If api_config is provided, it must have a url
        if 'api_config' in input_data:
            if not isinstance(input_data['api_config'], dict) or 'url' not in input_data['api_config']:
                logger.warning("api_config must be a dictionary with a url field")
                return False
        
        return True
    
    async def pre_process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare the input data for processing."""
        processed_data = input_data.copy()
        
        # Convert api_config to endpoints list format if provided
        if 'api_config' in processed_data and 'endpoints' not in processed_data:
            processed_data['endpoints'] = [processed_data['api_config']]
            del processed_data['api_config']
        
        # Convert endpoint dictionaries to APIEndpoint objects
        processed_data['endpoints'] = [
            APIEndpoint(**endpoint) if isinstance(endpoint, dict) else endpoint
            for endpoint in processed_data['endpoints']
        ]
        
        # Add default headers to each endpoint
        for endpoint in processed_data['endpoints']:
            endpoint.headers = {**self.default_headers, **endpoint.headers}
        
        return processed_data
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch data from specified API endpoints.
        
        Args:
            input_data: Dict containing:
                - endpoints: List of API endpoint configurations
                - create_documents: Whether to create documents (default: False)
                
        Returns:
            Dict with API responses and created documents
        """
        endpoints = input_data['endpoints']
        create_documents = input_data.get('create_documents', False)
        
        # Track processing time
        start_time = time.time()
        
        # Process all endpoints
        results = []
        created_docs = []
        errors = []
        
        for endpoint in endpoints:
            try:
                # Fetch data from the endpoint
                api_responses = await self._fetch_from_endpoint(endpoint)
                
                # Add to results
                for response in api_responses:
                    results.append(response.dict())
                
                # Create documents if requested
                if create_documents:
                    for response in api_responses:
                        if response.is_success:
                            doc_id = await self._create_document(response, input_data)
                            if doc_id:
                                created_docs.append(doc_id)
                
            except Exception as e:
                error_data = {
                    "url": endpoint.url,
                    "error": str(e),
                    "error_type": type(e).__name__
                }
                errors.append(error_data)
                logger.error(f"Error processing endpoint {endpoint.url}: {str(e)}")
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Return results
        result = {
            "responses": results,
            "processing_time": processing_time,
            "successful_requests": len([r for r in results if r.get("is_success", False)]),
            "failed_requests": len([r for r in results if not r.get("is_success", True)]),
            "errors": errors
        }
        
        if create_documents:
            result["created_documents"] = created_docs
        
        return result
    
    async def _fetch_from_endpoint(self, endpoint: APIEndpoint) -> List[APIResponse]:
        """Fetch data from an API endpoint, handling pagination if configured."""
        # Configure httpx client
        client_kwargs = {
            "timeout": endpoint.timeout,
            "follow_redirects": True,
            "headers": endpoint.headers
        }
        
        # Configure authentication
        if endpoint.auth_type:
            client_kwargs = await self._configure_auth(endpoint, client_kwargs)
        
        # Initialize the client
        async with httpx.AsyncClient(**client_kwargs) as client:
            # Check if pagination is configured
            if endpoint.pagination and endpoint.pagination.get('enabled', False):
                # Fetch multiple pages
                return await self._fetch_with_pagination(client, endpoint)
            else:
                # Fetch single response
                return [await self._make_request(client, endpoint)]
    
    async def _make_request(self, client, endpoint: APIEndpoint) -> APIResponse:
        """Make a single HTTP request and process the response."""
        method = endpoint.method.upper()
        request_start = time.time()
        error_message = None
        
        try:
            # Prepare request parameters
            request_kwargs = {
                "params": endpoint.params
            }
            
            # Add body for POST/PUT/PATCH requests
            if method in ["POST", "PUT", "PATCH"] and endpoint.body is not None:
                request_kwargs["json"] = endpoint.body
            
            # Make the request with retries
            response = None
            retries = endpoint.retry
            
            while retries >= 0:
                try:
                    response = await client.request(method, endpoint.url, **request_kwargs)
                    break  # Success, exit retry loop
                except httpx.TimeoutException:
                    retries -= 1
                    if retries < 0:
                        raise  # No more retries
                    await asyncio.sleep(1)  # Wait before retry
            
            # Calculate response time
            response_time = time.time() - request_start
            
            # Process response
            content_type = response.headers.get("content-type", "")
            is_json = "application/json" in content_type
            
            # Parse data
            if is_json:
                data = response.json()
            else:
                data = response.text
            
            # Check for a successful response
            is_success = 200 <= response.status_code < 300
            
            if not is_success:
                error_message = f"HTTP {response.status_code}: {response.reason_phrase}"
            
            # If content_path is specified and data is JSON, extract content
            if is_json and endpoint.content_path and is_success:
                data = self._extract_data_by_path(data, endpoint.content_path)
            
            # Build response object
            return APIResponse(
                url=str(response.url),
                status_code=response.status_code,
                response_time=response_time,
                content_type=content_type,
                data=data,
                headers=dict(response.headers),
                is_success=is_success,
                error_message=error_message
            )
            
        except Exception as e:
            # Handle request errors
            response_time = time.time() - request_start
            return APIResponse(
                url=endpoint.url,
                status_code=0,
                response_time=response_time,
                content_type="",
                data=None,
                headers={},
                is_success=False,
                error_message=str(e)
            )
    
    async def _fetch_with_pagination(self, client, endpoint: APIEndpoint) -> List[APIResponse]:
        """Fetch data from an API with pagination."""
        # Determine pagination strategy
        strategy_name = endpoint.pagination.get('strategy', 'offset')
        max_pages = endpoint.pagination.get('max_pages', 10)
        
        # Get the pagination strategy function
        if strategy_name in self.pagination_strategies:
            paginate_func = self.pagination_strategies[strategy_name]
        else:
            logger.warning(f"Unknown pagination strategy: {strategy_name}, defaulting to offset")
            paginate_func = self.pagination_strategies['offset']
        
        # Use the pagination strategy to fetch all pages
        return await paginate_func(client, endpoint, max_pages)
    
    async def _paginate_with_offset(self, client, endpoint: APIEndpoint, max_pages: int) -> List[APIResponse]:
        """Paginate using offset-based pagination."""
        offset_param = endpoint.pagination.get('offset_param', 'offset')
        limit_param = endpoint.pagination.get('limit_param', 'limit')
        limit = endpoint.pagination.get('limit', 100)
        
        responses = []
        more_data = True
        page = 0
        
        while more_data and page < max_pages:
            # Update params with current offset
            current_params = endpoint.params.copy()
            current_params[offset_param] = page * limit
            current_params[limit_param] = limit
            
            # Create a copy of the endpoint with updated params
            current_endpoint = APIEndpoint(
                **{**endpoint.dict(), "params": current_params}
            )
            
            # Make the request
            response = await self._make_request(client, current_endpoint)
            responses.append(response)
            
            # Check if we got data and should continue
            if not response.is_success or not response.data or (
                isinstance(response.data, list) and len(response.data) < limit
            ):
                more_data = False
            
            page += 1
        
        return responses
    
    async def _paginate_with_page(self, client, endpoint: APIEndpoint, max_pages: int) -> List[APIResponse]:
        """Paginate using page-based pagination."""
        page_param = endpoint.pagination.get('page_param', 'page')
        limit_param = endpoint.pagination.get('limit_param', 'per_page')
        limit = endpoint.pagination.get('limit', 100)
        
        responses = []
        more_data = True
        page = 1  # Page typically starts at 1
        
        while more_data and page <= max_pages:
            # Update params with current page
            current_params = endpoint.params.copy()
            current_params[page_param] = page
            current_params[limit_param] = limit
            
            # Create a copy of the endpoint with updated params
            current_endpoint = APIEndpoint(
                **{**endpoint.dict(), "params": current_params}
            )
            
            # Make the request
            response = await self._make_request(client, current_endpoint)
            responses.append(response)
            
            # Check if we got data and should continue
            if not response.is_success or not response.data or (
                isinstance(response.data, list) and len(response.data) < limit
            ):
                more_data = False
            
            page += 1
        
        return responses
    
    async def _paginate_with_cursor(self, client, endpoint: APIEndpoint, max_pages: int) -> List[APIResponse]:
        """Paginate using cursor-based pagination."""
        cursor_param = endpoint.pagination.get('cursor_param', 'cursor')
        cursor_path = endpoint.pagination.get('cursor_path', 'meta.next_cursor')
        
        responses = []
        cursor = None
        page = 0
        
        while page < max_pages:
            # Update params with current cursor if we have one
            current_params = endpoint.params.copy()
            if cursor:
                current_params[cursor_param] = cursor
            
            # Create a copy of the endpoint with updated params
            current_endpoint = APIEndpoint(
                **{**endpoint.dict(), "params": current_params}
            )
            
            # Make the request
            response = await self._make_request(client, current_endpoint)
            responses.append(response)
            
            # Check if we should continue
            if not response.is_success or not response.data:
                break
            
            # Extract next cursor
            cursor = self._extract_data_by_path(response.data, cursor_path)
            
            # If no cursor, we're done
            if not cursor:
                break
            
            page += 1
        
        return responses
    
    async def _paginate_with_link_header(self, client, endpoint: APIEndpoint, max_pages: int) -> List[APIResponse]:
        """Paginate using Link header (common in GitHub and other APIs)."""
        responses = []
        next_url = endpoint.url
        page = 0
        
        while next_url and page < max_pages:
            # Create a copy of the endpoint with the next URL
            current_endpoint = APIEndpoint(
                **{**endpoint.dict(), "url": next_url}
            )
            
            # Make the request
            response = await self._make_request(client, current_endpoint)
            responses.append(response)
            
            # Check if we should continue
            if not response.is_success:
                break
            
            # Extract next URL from Link header
            next_url = self._extract_next_url(response.headers.get('link', ''))
            page += 1
        
        return responses
    
    def _extract_next_url(self, link_header: str) -> Optional[str]:
        """Extract next URL from a Link header."""
        if not link_header:
            return None
        
        # Parse the Link header
        links = {}
        for link in link_header.split(','):
            parts = link.strip().split(';')
            if len(parts) < 2:
                continue
            
            url = parts[0].strip('<> ')
            for p in parts[1:]:
                if '=' in p:
                    name, value = p.split('=', 1)
                    if name.strip() == 'rel' and value.strip('" ') == 'next':
                        return url
        
        return None
    
    def _extract_data_by_path(self, data: Any, path: str) -> Any:
        """Extract data from a nested structure using a path string."""
        if not path:
            return data
        
        parts = path.split('.')
        current = data
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            elif isinstance(current, list) and part.isdigit():
                idx = int(part)
                if 0 <= idx < len(current):
                    current = current[idx]
                else:
                    return None
            else:
                return None
        
        return current
    
    async def _configure_auth(self, endpoint: APIEndpoint, client_kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Configure authentication based on auth_type."""
        auth_type = endpoint.auth_type
        auth_config = endpoint.auth_config
        
        if auth_type == "basic":
            # Basic authentication
            username = auth_config.get('username', '')
            password = auth_config.get('password', '')
            client_kwargs["auth"] = (username, password)
        
        elif auth_type == "bearer":
            # Bearer token authentication
            token = auth_config.get('token', '')
            if "headers" not in client_kwargs:
                client_kwargs["headers"] = {}
            client_kwargs["headers"]["Authorization"] = f"Bearer {token}"
        
        elif auth_type == "api_key":
            # API key authentication
            key = auth_config.get('key', '')
            key_name = auth_config.get('key_name', 'api_key')
            key_location = auth_config.get('key_location', 'header')
            
            if key_location == "header":
                if "headers" not in client_kwargs:
                    client_kwargs["headers"] = {}
                client_kwargs["headers"][key_name] = key
            
            elif key_location == "query":
                if "params" not in client_kwargs:
                    client_kwargs["params"] = {}
                client_kwargs["params"][key_name] = key
        
        elif auth_type == "oauth2":
            # OAuth2 authentication - would need a token refresh mechanism
            token = auth_config.get('access_token', '')
            if "headers" not in client_kwargs:
                client_kwargs["headers"] = {}
            client_kwargs["headers"]["Authorization"] = f"Bearer {token}"
        
        return client_kwargs
    
    async def _create_document(self, response: APIResponse, input_data: Dict[str, Any]) -> Optional[str]:
        """Create a document from API response data."""
        try:
            # Convert data to string representation
            if isinstance(response.data, (dict, list)):
                content = json.dumps(response.data, indent=2)
                content_type = "application/json"
            else:
                content = str(response.data)
                content_type = response.content_type or "text/plain"
            
            # Generate title from URL
            from urllib.parse import urlparse
            parsed_url = urlparse(response.url)
            title = f"API: {parsed_url.netloc}{parsed_url.path}"
            
            # Prepare document data
            doc_data = {
                "title": title,
                "content": content,
                "content_type": content_type,
                "source": response.url,
                "language": input_data.get('language', 'en'),
                "metadata": {
                    "api_source": True,
                    "retrieval_date": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime()),
                    "status_code": response.status_code,
                    "response_time": response.response_time,
                    "content_type": response.content_type
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
        # Add summary statistics
        if "responses" in result:
            data_count = 0
            
            for response in result["responses"]:
                if response.get("data") and response.get("is_success", False):
                    if isinstance(response["data"], list):
                        data_count += len(response["data"])
                    elif isinstance(response["data"], dict):
                        data_count += 1
            
            result["summary"] = {
                "total_requests": len(result["responses"]),
                "successful_requests": result.get("successful_requests", 0),
                "failed_requests": result.get("failed_requests", 0),
                "total_data_items": data_count
            }
        
        return result