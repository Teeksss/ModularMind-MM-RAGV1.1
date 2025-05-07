from typing import Dict, Any, List, Optional, Tuple
import logging
import asyncio
import time
import uuid
from datetime import datetime
import json

from app.core.settings import get_settings
from app.db.session import get_db
from app.models.query import QueryResult, Source
from app.services.vector_store import get_vector_store
from app.services.llm_service import get_llm_service
from app.services.document_service import get_document_service

settings = get_settings()
logger = logging.getLogger(__name__)


class QueryService:
    """
    Service for processing queries using RAG.
    
    Handles the entire RAG pipeline:
    1. Query analysis
    2. Document retrieval
    3. Context preparation
    4. LLM response generation
    5. Metadata gathering
    """
    
    def __init__(self):
        """Initialize the query service."""
        self.vector_store = get_vector_store()
        self.llm_service = get_llm_service()
        self.document_service = get_document_service()
    
    async def process_query(
        self,
        query: str,
        user_id: str,
        session_id: Optional[str] = None,
        language: str = "en",
        max_results: int = 5,
        include_sources: bool = True,
        context: List[Dict[str, Any]] = None
    ) -> QueryResult:
        """
        Process a user query using RAG.
        
        Args:
            query: The user's query
            user_id: User ID
            session_id: Optional session ID for context
            language: Query language
            max_results: Maximum number of sources to retrieve
            include_sources: Whether to include source content in the response
            context: Optional conversation context
            
        Returns:
            QueryResult with answer and sources
        """
        start_time = time.time()
        logger.info(f"Processing query: '{query}' for user {user_id}")
        
        # Get retrieval type from settings
        retrieval_type = settings.retrieval.retrieval_type
        
        # 1. Retrieve relevant documents
        if retrieval_type == "hybrid":
            # Use hybrid retrieval (combined dense + sparse)
            search_results = await self.vector_store.hybrid_search(
                query=query,
                k=max_results * 2,  # Get more results for potential filtering
                alpha=0.7  # Weight towards dense retrieval
            )
            
            # Extract relevant information
            sources = [
                {
                    "id": result.id,
                    "text": result.text,
                    "score": result.combined_score,
                    "metadata": result.metadata
                }
                for result in search_results
            ]
        
        elif retrieval_type == "dense":
            # Use dense vector retrieval
            search_results = await self.vector_store.similarity_search(
                query=query,
                k=max_results * 2
            )
            
            # Extract relevant information
            sources = [
                {
                    "id": result.id,
                    "text": result.text,
                    "score": result.score,
                    "metadata": result.metadata
                }
                for result in search_results
            ]
        
        else:
            # Sparse retrieval not implemented here
            # Would typically use BM25 or similar
            raise ValueError(f"Unsupported retrieval type: {retrieval_type}")
        
        # 2. Apply post-retrieval filtering and ranking
        if settings.retrieval.reranking_enabled and len(sources) > max_results:
            # In a real implementation, this would use a reranker model
            # For now, we'll just use the scores from retrieval
            sources = sorted(sources, key=lambda s: s["score"], reverse=True)
        
        # Apply similarity threshold
        sources = [s for s in sources if s["score"] >= settings.retrieval.similarity_threshold]
        
        # Limit to max_results
        sources = sources[:max_results]
        
        # 3. Prepare context from sources
        context_texts = []
        for source in sources:
            # Add source text to context
            source_text = f"Source (ID: {source['id']}): {source['text']}"
            context_texts.append(source_text)
        
        # Combine into a single context string
        combined_context = "\n\n".join(context_texts)
        
        # 4. Prepare conversation context if available
        conversation_context = ""
        if context and len(context) > 0:
            # Format conversation history for the prompt
            formatted_history = []
            for item in context[-5:]:  # Use last 5 items only
                if item["type"] == "query":
                    formatted_history.append(f"User: {item['content']}")
                elif item["type"] == "response":
                    formatted_history.append(f"Assistant: {item['content']}")
            
            conversation_context = "Previous conversation:\n" + "\n".join(formatted_history)
        
        # 5. Generate prompt for LLM
        prompt = self._generate_rag_prompt(
            query=query,
            context=combined_context,
            conversation_context=conversation_context,
            language=language
        )
        
        # 6. Call LLM to generate response
        system_prompt = self._get_system_prompt(language)
        
        try:
            answer = await self.llm_service.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.1,  # Lower temperature for more factual responses
                max_tokens=1024
            )
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            # Fallback to a simpler prompt if the main one fails
            try:
                fallback_prompt = f"Based on this information:\n\n{combined_context}\n\nPlease answer: {query}"
                answer = await self.llm_service.generate(
                    prompt=fallback_prompt,
                    system_prompt="You are a helpful assistant.",
                    temperature=0.1,
                    max_tokens=1024
                )
            except Exception as fallback_e:
                logger.error(f"Fallback generation also failed: {str(fallback_e)}")
                answer = "I'm sorry, but I couldn't generate a response at this time. Please try again later."
        
        # 7. Format and prepare sources for response
        formatted_sources = []
        if include_sources:
            for source in sources:
                # Get source document information
                doc_id = source["metadata"].get("document_id")
                source_info = await self._get_source_info(doc_id, source["id"], source["metadata"])
                
                formatted_sources.append(Source(
                    id=source["id"],
                    title=source_info.get("title", "Unknown Source"),
                    content_type=source_info.get("content_type", "text/plain"),
                    url=source_info.get("url"),
                    score=source["score"],
                    metadata=source_info.get("metadata", {})
                ))
        
        # 8. Save query to database for history
        query_id = await self._save_query(
            user_id=user_id,
            session_id=session_id,
            query=query,
            answer=answer,
            sources=[s.id for s in formatted_sources],
            language=language
        )
        
        # 9. Prepare and return the result
        processing_time = time.time() - start_time
        
        logger.info(f"Query processed in {processing_time:.2f}s with {len(formatted_sources)} sources")
        
        return QueryResult(
            query_id=query_id,
            answer=answer,
            sources=formatted_sources,
            processing_time=processing_time
        )
    
    def _generate_rag_prompt(
        self,
        query: str,
        context: str,
        conversation_context: str = "",
        language: str = "en"
    ) -> str:
        """
        Generate a prompt for RAG.
        
        Args:
            query: The user's query
            context: Retrieved context
            conversation_context: Optional conversation history
            language: Query language
            
        Returns:
            Formatted prompt
        """
        prompt = "Use the following retrieved information to answer the user's question.\n\n"
        
        if conversation_context:
            prompt += f"{conversation_context}\n\n"
        
        prompt += "Retrieved information:\n"
        prompt += f"{context}\n\n"
        
        prompt += "Answer the following question based on the retrieved information above. "
        prompt += "If the information doesn't contain the answer, say you don't know rather than making something up. "
        prompt += "Cite the source IDs when using information from a specific source.\n\n"
        
        prompt += f"Question: {query}\n\n"
        prompt += "Answer:"
        
        return prompt
    
    def _get_system_prompt(self, language: str) -> str:
        """Get system prompt based on language."""
        base_prompt = "You are a helpful assistant that answers questions based on the information provided. "
        base_prompt += "Your answers are clear, accurate, and based only on the context given. "
        base_prompt += "If you don't know something, say so rather than making up information."
        
        if language == "tr":
            return base_prompt + " Respond in Turkish."
        elif language == "de":
            return base_prompt + " Respond in German."
        elif language == "fr":
            return base_prompt + " Respond in French."
        else:
            return base_prompt + " Respond in English."
    
    async def _get_source_info(
        self,
        document_id: Optional[str],
        source_id: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get source document information.
        
        Args:
            document_id: Document ID if available
            source_id: Source ID
            metadata: Source metadata
            
        Returns:
            Source information
        """
        if not document_id:
            # If there's no document ID, just return the metadata
            return {
                "title": metadata.get("title", "Unknown"),
                "content_type": metadata.get("content_type", "text/plain"),
                "metadata": metadata
            }
        
        try:
            # Try to get document information
            document = await self.document_service.get_document(document_id)
            
            if document:
                return {
                    "title": document.title,
                    "content_type": document.content_type,
                    "metadata": {
                        **document.metadata,
                        **metadata
                    }
                }
        except Exception as e:
            logger.warning(f"Error getting document info: {str(e)}")
        
        # Fallback to metadata
        return {
            "title": metadata.get("title", "Unknown"),
            "content_type": metadata.get("content_type", "text/plain"),
            "metadata": metadata
        }
    
    async def _save_query(
        self,
        user_id: str,
        session_id: Optional[str],
        query: str,
        answer: str,
        sources: List[str],
        language: str
    ) -> str:
        """
        Save query to database for history.
        
        Args:
            user_id: User ID
            session_id: Session ID
            query: Query text
            answer: Generated answer
            sources: List of source IDs
            language: Query language
            
        Returns:
            Query ID
        """
        query_id = str(uuid.uuid4())
        
        async with get_db() as db:
            query = """
            INSERT INTO queries (
                id, user_id, session_id, query, answer, sources, language, created_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id
            """
            
            values = (
                query_id,
                user_id,
                session_id,
                query,
                answer,
                json.dumps(sources),
                language,
                datetime.now()
            )
            
            await db.execute(query, *values)
            
            return query_id
    
    async def get_query_history(
        self,
        user_id: str,
        session_id: Optional[str] = None,
        limit: int = 10,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get query history for a user.
        
        Args:
            user_id: User ID
            session_id: Optional session ID to filter by
            limit: Max number of results
            skip: Number of results to skip
            
        Returns:
            List of query history items
        """
        async with get_db() as db:
            if session_id:
                query = """
                SELECT id, user_id, session_id, query, answer, sources, language, created_at, feedback
                FROM queries
                WHERE user_id = $1 AND session_id = $2
                ORDER BY created_at DESC
                LIMIT $3 OFFSET $4
                """
                results = await db.fetch_all(query, user_id, session_id, limit, skip)
            else:
                query = """
                SELECT id, user_id, session_id, query, answer, sources, language, created_at, feedback
                FROM queries
                WHERE user_id = $1
                ORDER BY created_at DESC
                LIMIT $2 OFFSET $3
                """
                results = await db.fetch_all(query, user_id, limit, skip)
            
            history = []
            for row in results:
                item = dict(row)
                if item["sources"]:
                    item["sources"] = json.loads(item["sources"])
                if item["feedback"]:
                    item["feedback"] = json.loads(item["feedback"])
                history.append(item)
            
            return history
    
    async def get_query(self, query_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific query by ID."""
        async with get_db() as db:
            query = """
            SELECT id, user_id, session_id, query, answer, sources, language, created_at, feedback
            FROM queries
            WHERE id = $1
            """
            
            result = await db.fetch_one(query, query_id)
            
            if not result:
                return None
            
            item = dict(result)
            if item["sources"]:
                item["sources"] = json.loads(item["sources"])
            if item["feedback"]:
                item["feedback"] = json.loads(item["feedback"])
            
            return item
    
    async def save_feedback(
        self,
        query_id: str,
        user_id: str,
        feedback: Dict[str, Any]
    ) -> bool:
        """
        Save feedback for a query.
        
        Args:
            query_id: Query ID
            user_id: User ID (for verification)
            feedback: Feedback data
            
        Returns:
            True if successful
        """
        async with get_db() as db:
            # First verify that the query belongs to the user
            verify_query = """
            SELECT id FROM queries
            WHERE id = $1 AND user_id = $2
            """
            
            verify_result = await db.fetch_one(verify_query, query_id, user_id)
            
            if not verify_result:
                return False
            
            # Save feedback
            update_query = """
            UPDATE queries
            SET feedback = $1, updated_at = $2
            WHERE id = $3
            """
            
            await db.execute(
                update_query,
                json.dumps(feedback),
                datetime.now(),
                query_id
            )
            
            return True
    
    async def generate_similar_questions(
        self,
        query: str,
        user_id: str,
        count: int = 3
    ) -> List[str]:
        """
        Generate similar questions to a query.
        
        Args:
            query: The base query
            user_id: User ID
            count: Number of similar questions to generate
            
        Returns:
            List of similar questions
        """
        prompt = f"""
        Generate {count} different variations of the following question. 
        The variations should ask for similar information but be worded differently.
        
        Original question: {query}
        
        Return only the questions, one per line, without numbering or additional text.
        """
        
        try:
            result = await self.llm_service.generate(
                prompt=prompt,
                temperature=0.7,  # Higher temperature for variety
                max_tokens=200
            )
            
            # Parse the result into a list of questions
            questions = [q.strip() for q in result.split('\n') if q.strip()]
            
            # Keep only the specified count
            return questions[:count]
            
        except Exception as e:
            logger.error(f"Error generating similar questions: {str(e)}")
            return []


# Create a singleton instance
_query_service = QueryService()

def get_query_service() -> QueryService:
    """Get the query service singleton."""
    return _query_service