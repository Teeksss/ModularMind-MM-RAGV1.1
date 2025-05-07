from typing import Dict, Any, List, Optional, Tuple
import logging
import asyncio
import time
import uuid
from datetime import datetime

from app.core.settings import get_settings
from app.db.session import get_db
from app.models.document import EnrichmentStatus
from app.agents.orchestrator import get_orchestrator
from app.services.vector_store import get_vector_store
from app.services.document_service import get_document_service

settings = get_settings()
logger = logging.getLogger(__name__)


class EnrichmentService:
    """
    Service for enriching documents with metadata, summaries, 
    semantic expansion, and other enrichments.
    
    This service coordinates the enrichment pipeline and manages 
    the execution of various enrichment agents.
    """
    
    def __init__(self):
        """Initialize the enrichment service."""
        self.document_service = get_document_service()
        self.orchestrator = get_orchestrator()
        self.vector_store = get_vector_store()
        
        # Track active enrichment processes
        self.active_enrichments = set()
    
    async def _update_enrichment_status(self, doc_id: str, status: EnrichmentStatus):
        """Update the enrichment status of a document."""
        await self.document_service.update_enrichment_status(doc_id, status)
    
    async def _store_enrichment(self, doc_id: str, enrichment_type: str, data: Dict[str, Any], agent: str):
        """Store an enrichment result in the database."""
        enrichment_id = str(uuid.uuid4())
        
        async with get_db() as db:
            query = """
            INSERT INTO document_enrichments (id, document_id, type, data, created_at, agent)
            VALUES ($1, $2, $3, $4, $5, $6)
            """
            
            values = (
                enrichment_id,
                doc_id,
                enrichment_type,
                data,
                datetime.now(),
                agent
            )
            
            await db.execute(query, *values)
            
            logger.info(f"Stored {enrichment_type} enrichment for document {doc_id}")
    
    async def _process_synthetic_qa(self, doc_id: str, content: str, metadata: Dict[str, Any]):
        """Process synthetic QA generation and store results in both DB and vector store."""
        if not settings.enrichment.synthetic_qa_enabled:
            logger.info("Synthetic QA generation is disabled")
            return
        
        # Get the document's language
        language = metadata.get("language", settings.multilingual.default_language)
        
        # Process synthetic QA generation
        synthetic_qa_pipeline = ["SyntheticQAGeneratorAgent"]
        
        qa_results = await self.orchestrator.execute_pipeline(
            input_data={"document_content": content, "document_id": doc_id, "language": language},
            pipeline=synthetic_qa_pipeline,
            execution_mode="serial"
        )
        
        # Check if we got valid results
        if not qa_results or not qa_results[0].success:
            logger.warning(f"Failed to generate synthetic QA for document {doc_id}")
            return
        
        # Extract QA pairs
        qa_pairs = qa_results[0].data.get("qa_pairs", [])
        
        if not qa_pairs:
            logger.info(f"No synthetic QA pairs generated for document {doc_id}")
            return
        
        # Store QA pairs in database
        for i, qa_pair in enumerate(qa_pairs):
            qa_id = str(uuid.uuid4())
            
            async with get_db() as db:
                query = """
                INSERT INTO synthetic_qa (id, document_id, question, answer, relevance_score, created_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
                """
                
                values = (
                    qa_id,
                    doc_id,
                    qa_pair["question"],
                    qa_pair["answer"],
                    qa_pair.get("relevance_score", 1.0),
                    datetime.now()
                )
                
                result = await db.fetch_one(query, *values)
            
            # Add to vector store
            combined_text = f"Q: {qa_pair['question']}\nA: {qa_pair['answer']}"
            metadata = {
                "document_id": doc_id,
                "qa_id": qa_id,
                "type": "synthetic_qa",
                "language": language
            }
            
            embedding_id = await self.vector_store.add_text(
                text=combined_text,
                metadata=metadata
            )
            
            # Update synthetic_qa record with embedding ID
            if embedding_id:
                async with get_db() as db:
                    await db.execute(
                        "UPDATE synthetic_qa SET embedding_id = $1 WHERE id = $2",
                        embedding_id, qa_id
                    )
        
        # Store enrichment metadata
        await self._store_enrichment(
            doc_id=doc_id,
            enrichment_type="synthetic_qa",
            data={"count": len(qa_pairs)},
            agent="SyntheticQAGeneratorAgent"
        )
        
        logger.info(f"Generated and stored {len(qa_pairs)} synthetic QA pairs for document {doc_id}")
    
    async def _analyze_document_content(self, doc_id: str, content: str, language: str):
        """Analyze document content to determine appropriate agents to use."""
        # In a more sophisticated implementation, you would use AI to analyze
        # the document and decide on the appropriate enrichment pipeline.
        # For now, we'll use a simple length-based heuristic.
        
        pipeline = []
        
        # Always include metadata extraction
        pipeline.append("MetadataExtractorAgent")
        
        # Add summarization for longer documents
        if len(content) > 1000:
            pipeline.append("SummarizationAgent")
        
        # Add semantic expansion for all documents
        pipeline.append("SemanticExpanderAgent")
        
        # Add contextual tagging for all documents
        pipeline.append("ContextualTaggerAgent")
        
        # Add relation building for longer documents
        if len(content) > 3000:
            pipeline.append("RelationBuilderAgent")
        
        # Filter by actually available agents
        available_agents = set(self.orchestrator.get_active_agents())
        pipeline = [agent for agent in pipeline if agent in available_agents]
        
        return pipeline
    
    async def enrich_document(self, doc_id: str, content: str, language: str, content_type: str = "text/plain"):
        """
        Enrich a document with metadata, summaries, and other information.
        
        Args:
            doc_id: Document ID
            content: Document content text
            language: Document language code
            content_type: Document content type
        """
        # Check if this document is already being enriched
        if doc_id in self.active_enrichments:
            logger.warning(f"Document {doc_id} is already being enriched, skipping")
            return
        
        # Mark as being processed
        self.active_enrichments.add(doc_id)
        
        try:
            # Update document status to PROCESSING
            await self._update_enrichment_status(doc_id, EnrichmentStatus.PROCESSING)
            
            # Determine appropriate agents based on content analysis
            pipeline = await self._analyze_document_content(doc_id, content, language)
            
            if not pipeline:
                logger.warning(f"No active agents available for enrichment")
                await self._update_enrichment_status(doc_id, EnrichmentStatus.SKIPPED)
                return
            
            # Prepare input data for agents
            input_data = {
                "document_content": content,
                "document_id": doc_id,
                "content_type": content_type,
                "language": language
            }
            
            # Execute the enrichment pipeline
            logger.info(f"Starting enrichment of document {doc_id} with agents: {', '.join(pipeline)}")
            
            results = await self.orchestrator.execute_pipeline(
                input_data=input_data,
                pipeline=pipeline,
                execution_mode="serial"  # Process in sequence, passing results to next agent
            )
            
            # Process and store results
            if not results:
                logger.error(f"No results returned from enrichment pipeline for document {doc_id}")
                await self._update_enrichment_status(doc_id, EnrichmentStatus.FAILED)
                return
            
            # Track success/failure
            all_successful = True
            metadata = {}
            
            for result in results:
                if not result.success:
                    logger.error(f"Agent {result.agent_name} failed: {result.error}")
                    all_successful = False
                    continue
                
                # Store enrichment data by type
                if result.agent_name == "MetadataExtractorAgent" and "metadata" in result.data:
                    await self._store_enrichment(
                        doc_id=doc_id,
                        enrichment_type="metadata",
                        data=result.data["metadata"],
                        agent=result.agent_name
                    )
                    metadata = result.data["metadata"]
                
                elif result.agent_name == "SummarizationAgent" and "summary" in result.data:
                    await self._store_enrichment(
                        doc_id=doc_id,
                        enrichment_type="summary",
                        data={"summary": result.data["summary"]},
                        agent=result.agent_name
                    )
                
                elif result.agent_name == "SemanticExpanderAgent" and "expansions" in result.data:
                    await self._store_enrichment(
                        doc_id=doc_id,
                        enrichment_type="semantic_expansion",
                        data={"expansions": result.data["expansions"]},
                        agent=result.agent_name
                    )
                
                elif result.agent_name == "ContextualTaggerAgent" and "tags" in result.data:
                    await self._store_enrichment(
                        doc_id=doc_id,
                        enrichment_type="tags",
                        data={"tags": result.data["tags"]},
                        agent=result.agent_name
                    )
                
                elif result.agent_name == "RelationBuilderAgent" and "relations" in result.data:
                    await self._store_enrichment(
                        doc_id=doc_id,
                        enrichment_type="relations",
                        data={"relations": result.data["relations"]},
                        agent=result.agent_name
                    )
            
            # Generate synthetic QA pairs if enabled
            if settings.enrichment.synthetic_qa_enabled:
                await self._process_synthetic_qa(doc_id, content, {"language": language, **metadata})
            
            # Update document status
            if all_successful:
                await self._update_enrichment_status(doc_id, EnrichmentStatus.COMPLETED)
                logger.info(f"Completed enrichment of document {doc_id}")
            else:
                await self._update_enrichment_status(doc_id, EnrichmentStatus.FAILED)
                logger.warning(f"Enrichment of document {doc_id} completed with some failures")
        
        except Exception as e:
            # Handle any unexpected errors
            logger.error(f"Error enriching document {doc_id}: {str(e)}", exc_info=True)
            await self._update_enrichment_status(doc_id, EnrichmentStatus.FAILED)
        
        finally:
            # Remove from active enrichments
            self.active_enrichments.remove(doc_id)
    
    async def get_enrichments(self, doc_id: str, enrichment_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get enrichments for a document.
        
        Args:
            doc_id: Document ID
            enrichment_type: Optional type filter
            
        Returns:
            List of enrichments
        """
        async with get_db() as db:
            if enrichment_type:
                query = """
                SELECT id, document_id, type, data, created_at, agent
                FROM document_enrichments
                WHERE document_id = $1 AND type = $2
                ORDER BY created_at DESC
                """
                results = await db.fetch_all(query, doc_id, enrichment_type)
            else:
                query = """
                SELECT id, document_id, type, data, created_at, agent
                FROM document_enrichments
                WHERE document_id = $1
                ORDER BY type, created_at DESC
                """
                results = await db.fetch_all(query, doc_id)
            
            return [dict(row) for row in results]
    
    async def get_synthetic_qa(self, doc_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get synthetic QA pairs for a document."""
        async with get_db() as db:
            query = """
            SELECT id, document_id, question, answer, relevance_score, created_at
            FROM synthetic_qa
            WHERE document_id = $1
            ORDER BY relevance_score DESC
            LIMIT $2
            """
            results = await db.fetch_all(query, doc_id, limit)
            
            return [dict(row) for row in results]


# Create a singleton instance
_enrichment_service = EnrichmentService()

def get_enrichment_service() -> EnrichmentService:
    """Get the enrichment service singleton."""
    return _enrichment_service