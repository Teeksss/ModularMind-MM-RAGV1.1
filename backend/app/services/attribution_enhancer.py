from typing import Dict, Any, List, Optional, Union
import logging
import re
from pydantic import BaseModel, Field

from app.core.settings import get_settings
from app.services.retrievers.base import SearchResult
from app.services.llm_service import get_llm_service

settings = get_settings()
logger = logging.getLogger(__name__)


class Attribution(BaseModel):
    """Model for a source attribution."""
    id: str
    text: str  # Cited text
    source_id: str
    source_title: Optional[str] = None
    source_url: Optional[str] = None
    source_type: Optional[str] = None
    location: Optional[str] = None  # Citation location (page number, etc.)
    relevance: float = 1.0
    index: int  # Index in the citations list


class SourceAttribution(BaseModel):
    """Model for source attributions in a response."""
    response: str  # Response with citation markers
    citations: List[Attribution] = Field(default_factory=list)
    sources: Dict[str, Any] = Field(default_factory=dict)
    markdown: Optional[str] = None  # Markdown formatted response with citations
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AttributionEnhancer:
    """
    Enhancer for adding source attributions to responses.
    
    Analyzes LLM responses against source documents to attribute
    information to specific sources and creates properly formatted
    citations in the final output.
    """
    
    def __init__(
        self,
        citation_style: str = "numbered",
        include_urls: bool = True,
        link_citations: bool = True,
        citation_format: str = "markdown"
    ):
        """
        Initialize the attribution enhancer.
        
        Args:
            citation_style: Style of citations ('numbered', 'author-date', 'superscript')
            include_urls: Whether to include URLs in citations
            link_citations: Whether to make citations clickable links
            citation_format: Output format for citations ('markdown', 'html', 'text')
        """
        self.citation_style = citation_style
        self.include_urls = include_urls
        self.link_citations = link_citations
        self.citation_format = citation_format
        self.llm_service = get_llm_service()
        
        logger.info(
            f"Initialized AttributionEnhancer with citation_style={citation_style}, "
            f"citation_format={citation_format}"
        )
    
    async def enhance(
        self,
        response: str,
        sources: List[SearchResult],
        query: Optional[str] = None,
        auto_detect: bool = True
    ) -> SourceAttribution:
        """
        Enhance a response with source attributions.
        
        Args:
            response: The LLM response to enhance
            sources: The source documents used for the response
            query: Original query for context
            auto_detect: Whether to automatically detect attributions
            
        Returns:
            Enhanced response with citations
        """
        if not sources:
            # No sources, return original response
            return SourceAttribution(
                response=response,
                citations=[],
                sources={},
                markdown=response
            )
        
        # Analyze which parts of the response come from which sources
        if auto_detect:
            attributions = await self._detect_attributions(response, sources, query)
        else:
            # Direct mapping - assume LLM has added citation markers
            attributions = self._extract_explicit_citations(response, sources)
        
        # Add citation markers to the response
        enhanced_response, citations = self._add_citation_markers(response, attributions, sources)
        
        # Create source index
        source_index = self._build_source_index(citations, sources)
        
        # Generate markdown with citations
        markdown_response = self._format_as_markdown(enhanced_response, citations, source_index)
        
        # Create SourceAttribution result
        attribution_result = SourceAttribution(
            response=enhanced_response,
            citations=citations,
            sources=source_index,
            markdown=markdown_response,
            metadata={
                "citation_style": self.citation_style,
                "citation_format": self.citation_format,
                "auto_detect": auto_detect
            }
        )
        
        return attribution_result
    
    async def _detect_attributions(
        self,
        response: str,
        sources: List[SearchResult],
        query: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Detect which parts of the response are attributable to which sources."""
        # Prepare source snippets for analysis
        source_snippets = []
        for i, source in enumerate(sources[:5]):  # Limit to top 5 sources
            source_snippets.append({
                "id": source.id,
                "text": source.text[:1000],  # Limit length for LLM processing
                "title": source.metadata.get("title", f"Source {i+1}"),
                "index": i
            })
        
        # Create prompt for attribution detection
        prompt = """
        Analyze the following AI response and determine which parts should be attributed to which source documents.
        
        Original query: {query}
        
        AI response:
        {response}
        
        Source documents:
        {sources}
        
        For each sentence or claim in the AI response, identify if it should be attributed to one of the sources.
        Return your analysis as a JSON array of attribution objects, where each object has:
        - "text": The text from the response that should be attributed
        - "source_id": The ID of the source document this is from
        - "confidence": A number between 0 and 1 indicating your confidence in this attribution
        
        Only include attributions where you are reasonably confident (>0.5).
        Only include the JSON array, nothing else.
        """
        
        # Format source documents for the prompt
        sources_text = "\n\n".join([
            f"Source {s['index']+1} (ID: {s['id']}): {s['title']}\n{s['text'][:300]}..."
            for s in source_snippets
        ])
        
        # Call LLM to detect attributions
        try:
            formatted_prompt = prompt.format(
                query=query or "unknown query",
                response=response,
                sources=sources_text
            )
            
            attributions = await self.llm_service.generate_json(
                prompt=formatted_prompt,
                temperature=0.1
            )
            
            if not isinstance(attributions, list):
                logger.warning(f"Unexpected attribution format from LLM: {type(attributions)}")
                return []
            
            return attributions
            
        except Exception as e:
            logger.error(f"Error detecting attributions: {str(e)}")
            return []
    
    def _extract_explicit_citations(
        self,
        response: str,
        sources: List[SearchResult]
    ) -> List[Dict[str, Any]]:
        """Extract explicit citation markers from response."""
        # Look for citation patterns [1], [2], etc.
        citation_pattern = r'\[(\d+)\]'
        matches = re.finditer(citation_pattern, response)
        
        attributions = []
        for match in matches:
            citation_num = int(match.group(1))
            if 1 <= citation_num <= len(sources):
                # Extract the sentence containing the citation
                # This is a simplified approach - a more sophisticated approach would
                # determine exactly what content is being cited
                start = max(0, match.start() - 100)
                end = min(len(response), match.end() + 100)
                text_around = response[start:end]
                
                # Find sentence boundaries
                sentence_pattern = r'[^.!?]*[.!?]'
                sentence_matches = re.finditer(sentence_pattern, text_around)
                for sentence_match in sentence_matches:
                    if match.start() - start <= sentence_match.end() and match.start() - start >= sentence_match.start():
                        attributed_text = text_around[sentence_match.start():sentence_match.end()]
                        
                        attributions.append({
                            "text": attributed_text,
                            "source_id": sources[citation_num-1].id,
                            "confidence": 0.9
                        })
                        break
        
        return attributions
    
    def _add_citation_markers(
        self,
        response: str,
        attributions: List[Dict[str, Any]],
        sources: List[SearchResult]
    ) -> Tuple[str, List[Attribution]]:
        """Add citation markers to the response."""
        # Sort attributions by position in the response
        # This is an approximation as we don't have exact positions
        result = response
        citations = []
        
        # Create source ID to index mapping
        source_indexes = {source.id: i for i, source in enumerate(sources)}
        
        # Process attributions
        for i, attr in enumerate(attributions):
            source_id = attr.get("source_id")
            text = attr.get("text", "")
            confidence = attr.get("confidence", 0.0)
            
            if not source_id or not text or confidence < 0.5:
                continue
            
            # Find source index
            source_index = source_indexes.get(source_id)
            if source_index is None:
                continue
            
            # Create citation
            citation_index = len(citations) + 1
            citation = Attribution(
                id=f"cite-{citation_index}",
                text=text,
                source_id=source_id,
                source_title=sources[source_index].metadata.get("title"),
                source_url=sources[source_index].metadata.get("url"),
                source_type=sources[source_index].metadata.get("content_type", "text"),
                relevance=confidence,
                index=citation_index
            )
            
            # Add to citations list
            citations.append(citation)
            
            # Replace text with cited version
            # We only process non-overlapping text segments
            if text in result and f"[{citation_index}]" not in result:
                # Create citation marker based on style
                if self.citation_style == "numbered":
                    citation_marker = f"[{citation_index}]"
                elif self.citation_style == "superscript":
                    citation_marker = f"<sup>{citation_index}</sup>"
                else:  # author-date
                    author = sources[source_index].metadata.get("author", "Source")
                    date = sources[source_index].metadata.get("date", "n.d.")
                    citation_marker = f"({author}, {date})"
                
                # Add marker after the attributed text
                # This is a simplistic approach; it assumes non-overlapping attributions
                result = result.replace(text, text + citation_marker, 1)
        
        return result, citations
    
    def _build_source_index(
        self,
        citations: List[Attribution],
        sources: List[SearchResult]
    ) -> Dict[str, Any]:
        """Build a source index from citations."""
        source_index = {}
        
        # Group citations by source
        for citation in citations:
            if citation.source_id not in source_index:
                # Find the source in the original list
                source = next((s for s in sources if s.id == citation.source_id), None)
                
                if source:
                    # Extract metadata
                    title = source.metadata.get("title", "Untitled Source")
                    url = source.metadata.get("url")
                    content_type = source.metadata.get("content_type", "text")
                    author = source.metadata.get("author")
                    date = source.metadata.get("date")
                    
                    source_index[citation.source_id] = {
                        "id": citation.source_id,
                        "title": title,
                        "url": url,
                        "content_type": content_type,
                        "author": author,
                        "date": date,
                        "citations": [citation.index]
                    }
                else:
                    # Source wasn't found in the original list
                    source_index[citation.source_id] = {
                        "id": citation.source_id,
                        "title": citation.source_title or f"Source {citation.index}",
                        "url": citation.source_url,
                        "content_type": citation.source_type or "text",
                        "citations": [citation.index]
                    }
            else:
                # Add citation to existing source
                source_index[citation.source_id]["citations"].append(citation.index)
        
        return source_index
    
    def _format_as_markdown(
        self,
        response: str,
        citations: List[Attribution],
        source_index: Dict[str, Any]
    ) -> str:
        """Format the response with citations as markdown."""
        if not citations:
            return response
        
        # Format response with markdown citation markers
        markdown_response = response
        
        # Add sources section
        markdown_response += "\n\n---\n\n### Sources\n\n"
        
        # Format sources as numbered list
        for i, source_id in enumerate(source_index):
            source = source_index[source_id]
            source_text = f"{i+1}. **{source['title']}**"
            
            if source.get("author") and source.get("date"):
                source_text += f" by {source['author']} ({source['date']})"
            
            if source.get("url") and self.include_urls:
                if self.link_citations:
                    source_text += f" [Link]({source['url']})"
                else:
                    source_text += f" - {source['url']}"
            
            markdown_response += source_text + "\n"
        
        return markdown_response