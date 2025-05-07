from typing import Dict, Any, List, Optional, Union, Tuple
import logging
import asyncio
import time
import uuid
import json
import numpy as np
from pydantic import BaseModel, Field

from app.core.settings import get_settings
from app.services.llm_service import get_llm_service

settings = get_settings()
logger = logging.getLogger(__name__)


class VectorMetrics(BaseModel):
    """Metrics for vector store operations."""
    total_vectors: int = 0
    total_queries: int = 0
    avg_query_time_ms: float = 0
    dimensions: int = settings.vector_store.vector_dimension
    last_updated: float = time.time()


class VectorSearchResult(BaseModel):
    """Result of a vector search operation."""
    id: str
    text: str
    score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SparseSearchResult(BaseModel):
    """Result of a sparse search operation."""
    id: str
    text: str
    score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class HybridSearchResult(BaseModel):
    """Result of a hybrid search operation."""
    id: str
    text: str
    dense_score: float
    sparse_score: float
    combined_score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class VectorStoreService:
    """
    Service for vector storage and retrieval operations.
    
    Supports multiple vector database backends:
    - Qdrant
    - FAISS
    - Milvus
    """
    
    def __init__(self):
        """Initialize the vector store service."""
        self.llm_service = get_llm_service()
        self.metrics = VectorMetrics()
        self.vector_db_type = settings.vector_store.vector_db_type
        self.vector_dimension = settings.vector_store.vector_dimension
        self.collection_name = settings.vector_store.collection_name
        
        # Initialize the appropriate vector store client
        self._client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the vector store client based on configuration."""
        if self.vector_db_type == "qdrant":
            try:
                from qdrant_client import QdrantClient
                from qdrant_client.http import models as qdrant_models
                
                self._client = QdrantClient(
                    url=settings.vector_store.vector_db_url,
                    api_key=settings.vector_store.vector_db_api_key or None,
                    timeout=30.0
                )
                
                # Store Qdrant-specific models for later use
                self._qdrant_models = qdrant_models
                
            except ImportError:
                logger.error("Qdrant client not available. Please install qdrant-client.")
                raise
        
        elif self.vector_db_type == "faiss":
            try:
                import faiss
                
                # For FAISS, we'll store vectors in memory and save to disk periodically
                self._faiss_index = faiss.IndexFlatL2(self.vector_dimension)
                self._faiss_ids = []
                self._faiss_metadata = {}
                self._faiss_texts = {}
                
            except ImportError:
                logger.error("FAISS not available. Please install faiss-cpu or faiss-gpu.")
                raise
        
        elif self.vector_db_type == "milvus":
            try:
                from pymilvus import Collection, connections
                
                # Connect to Milvus
                connections.connect(
                    alias="default",
                    host=settings.vector_store.vector_db_url.split("://")[1].split(":")[0],
                    port=settings.vector_store.vector_db_url.split("://")[1].split(":")[1],
                )
                
                # Get collection
                self._client = Collection(self.collection_name)
                
            except ImportError:
                logger.error("Milvus client not available. Please install pymilvus.")
                raise
        
        else:
            raise ValueError(f"Unsupported vector DB type: {self.vector_db_type}")
    
    async def _ensure_collection(self):
        """Ensure the collection exists in the vector store."""
        if self.vector_db_type == "qdrant":
            # Check if collection exists
            collections = self._client.get_collections()
            collection_names = [c.name for c in collections.collections]
            
            if self.collection_name not in collection_names:
                # Create collection
                self._client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=self._qdrant_models.VectorParams(
                        size=self.vector_dimension,
                        distance=self._qdrant_models.Distance.COSINE,
                    )
                )
                logger.info(f"Created Qdrant collection: {self.collection_name}")
        
        elif self.vector_db_type == "milvus":
            # Check if collection exists
            from pymilvus import utility
            
            if not utility.has_collection(self.collection_name):
                # Create collection
                from pymilvus import FieldSchema, CollectionSchema, DataType, Collection
                
                fields = [
                    FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=100),
                    FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
                    FieldSchema(name="metadata", dtype=DataType.JSON),
                    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.vector_dimension),
                ]
                
                schema = CollectionSchema(fields)
                
                self._client = Collection(
                    name=self.collection_name,
                    schema=schema,
                    using="default"
                )
                
                # Create index
                self._client.create_index(
                    field_name="embedding",
                    index_params={
                        "metric_type": "COSINE",
                        "index_type": "IVF_FLAT",
                        "params": {"nlist": 1024}
                    }
                )
                
                logger.info(f"Created Milvus collection: {self.collection_name}")
    
    async def _generate_embeddings(self, text: str) -> np.ndarray:
        """
        Generate embeddings for text using the configured model.
        
        Args:
            text: Text to embed
            
        Returns:
            Numpy array of embeddings
        """
        # Use OpenAI embeddings
        if settings.embeddings.embedding_model.startswith("text-embedding"):
            import openai
            
            client = openai.AsyncClient(api_key=settings.llm.llm_api_key)
            
            response = await client.embeddings.create(
                model=settings.embeddings.embedding_model,
                input=text
            )
            
            return np.array(response.data[0].embedding)
        
        # Use sentence-transformers
        elif settings.embeddings.embedding_model.startswith("sentence-transformers"):
            from sentence_transformers import SentenceTransformer
            
            # Load model (this could be cached)
            model_name = settings.embeddings.embedding_model.replace("sentence-transformers/", "")
            model = SentenceTransformer(model_name)
            
            # Generate embeddings
            embeddings = model.encode(text)
            
            return np.array(embeddings)
        
        else:
            raise ValueError(f"Unsupported embedding model: {settings.embeddings.embedding_model}")
    
    async def add_text(self, text: str, metadata: Dict[str, Any] = None) -> str:
        """
        Add text to the vector store.
        
        Args:
            text: Text to add
            metadata: Optional metadata
            
        Returns:
            ID of the added vector
        """
        # Ensure collection exists
        await self._ensure_collection()
        
        # Generate embeddings
        embedding = await self._generate_embeddings(text)
        
        # Generate ID
        vector_id = str(uuid.uuid4())
        
        # Add to vector store
        if self.vector_db_type == "qdrant":
            self._client.upsert(
                collection_name=self.collection_name,
                points=[
                    self._qdrant_models.PointStruct(
                        id=vector_id,
                        vector=embedding.tolist(),
                        payload={
                            "text": text,
                            "metadata": metadata or {}
                        }
                    )
                ]
            )
        
        elif self.vector_db_type == "faiss":
            # Add to FAISS index
            self._faiss_index.add(np.array([embedding], dtype=np.float32))
            
            # Store metadata
            self._faiss_ids.append(vector_id)
            self._faiss_texts[vector_id] = text
            self._faiss_metadata[vector_id] = metadata or {}
        
        elif self.vector_db_type == "milvus":
            # Insert into Milvus
            self._client.insert([
                [vector_id],  # id
                [text],       # text
                [json.dumps(metadata or {})],  # metadata
                [embedding.tolist()]  # embedding
            ])
        
        # Update metrics
        self.metrics.total_vectors += 1
        self.metrics.last_updated = time.time()
        
        return vector_id
    
    async def add_texts(self, texts: List[str], metadatas: List[Dict[str, Any]] = None) -> List[str]:
        """
        Add multiple texts to the vector store.
        
        Args:
            texts: List of texts to add
            metadatas: Optional list of metadata dicts
            
        Returns:
            List of IDs for the added vectors
        """
        if metadatas is None:
            metadatas = [{} for _ in texts]
        
        if len(texts) != len(metadatas):
            raise ValueError("Number of texts and metadatas must match")
        
        # Ensure collection exists
        await self._ensure_collection()
        
        # Generate embeddings for all texts
        embeddings = []
        for text in texts:
            embedding = await self._generate_embeddings(text)
            embeddings.append(embedding)
        
        # Generate IDs
        vector_ids = [str(uuid.uuid4()) for _ in texts]
        
        # Add to vector store
        if self.vector_db_type == "qdrant":
            points = [
                self._qdrant_models.PointStruct(
                    id=vector_id,
                    vector=embedding.tolist(),
                    payload={
                        "text": text,
                        "metadata": metadata
                    }
                )
                for vector_id, embedding, text, metadata in zip(vector_ids, embeddings, texts, metadatas)
            ]
            
            self._client.upsert(
                collection_name=self.collection_name,
                points=points
            )
        
        elif self.vector_db_type == "faiss":
            # Add to FAISS index
            self._faiss_index.add(np.array(embeddings, dtype=np.float32))
            
            # Store metadata
            for i, vector_id in enumerate(vector_ids):
                self._faiss_ids.append(vector_id)
                self._faiss_texts[vector_id] = texts[i]
                self._faiss_metadata[vector_id] = metadatas[i]
        
        elif self.vector_db_type == "milvus":
            # Insert into Milvus
            data = [
                vector_ids,  # id
                texts,       # text
                [json.dumps(m) for m in metadatas],  # metadata
                [e.tolist() for e in embeddings]  # embedding
            ]
            
            self._client.insert(data)
        
        # Update metrics
        self.metrics.total_vectors += len(texts)
        self.metrics.last_updated = time.time()
        
        return vector_ids
    
    async def similarity_search(
        self, 
        query: str, 
        k: int = 5, 
        filter: Dict[str, Any] = None
    ) -> List[VectorSearchResult]:
        """
        Perform similarity search using vector embeddings.
        
        Args:
            query: Query text
            k: Number of results to return
            filter: Optional filter for the search
            
        Returns:
            List of search results
        """
        start_time = time.time()
        
        # Generate embeddings for query
        query_embedding = await self._generate_embeddings(query)
        
        # Perform search
        if self.vector_db_type == "qdrant":
            search_filter = None
            if filter:
                # Convert filter to Qdrant filter format
                search_filter = self._convert_to_qdrant_filter(filter)
            
            results = self._client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding.tolist(),
                limit=k,
                query_filter=search_filter
            )
            
            # Convert to VectorSearchResult objects
            search_results = [
                VectorSearchResult(
                    id=str(result.id),
                    text=result.payload["text"],
                    score=float(result.score),
                    metadata=result.payload.get("metadata", {})
                )
                for result in results
            ]
        
        elif self.vector_db_type == "faiss":
            # Search in FAISS
            if len(self._faiss_ids) == 0:
                return []
            
            # Perform search
            scores, indices = self._faiss_index.search(
                np.array([query_embedding], dtype=np.float32),
                k
            )
            
            # Convert to VectorSearchResult objects
            search_results = []
            for i, idx in enumerate(indices[0]):
                if idx == -1 or idx >= len(self._faiss_ids):
                    continue
                
                vector_id = self._faiss_ids[idx]
                
                # Apply filter if provided
                if filter:
                    metadata = self._faiss_metadata[vector_id]
                    if not self._matches_filter(metadata, filter):
                        continue
                
                search_results.append(
                    VectorSearchResult(
                        id=vector_id,
                        text=self._faiss_texts[vector_id],
                        score=float(scores[0][i]),
                        metadata=self._faiss_metadata[vector_id]
                    )
                )
        
        elif self.vector_db_type == "milvus":
            # Prepare filter
            expr = None
            if filter:
                # Convert filter to Milvus expression
                expr = self._convert_to_milvus_filter(filter)
            
            # Perform search
            self._client.load()
            results = self._client.search(
                data=[query_embedding.tolist()],
                anns_field="embedding",
                param={
                    "metric_type": "COSINE",
                    "params": {"nprobe": 10},
                },
                limit=k,
                expr=expr,
                output_fields=["text", "metadata"]
            )
            
            # Convert to VectorSearchResult objects
            search_results = []
            for hits in results:
                for hit in hits:
                    metadata = json.loads(hit.entity.get('metadata', '{}'))
                    search_results.append(
                        VectorSearchResult(
                            id=hit.id,
                            text=hit.entity.get('text', ''),
                            score=hit.distance,
                            metadata=metadata
                        )
                    )
        
        # Update metrics
        query_time = time.time() - start_time
        self.metrics.total_queries += 1
        self.metrics.avg_query_time_ms = (
            (self.metrics.avg_query_time_ms * (self.metrics.total_queries - 1) + query_time * 1000) /
            self.metrics.total_queries
        )
        
        return search_results
    
    async def hybrid_search(
        self, 
        query: str, 
        k: int = 5, 
        filter: Dict[str, Any] = None,
        alpha: float = 0.5  # Weight for dense vs sparse scoring (0 = all sparse, 1 = all dense)
    ) -> List[HybridSearchResult]:
        """
        Perform hybrid search using both vector embeddings and sparse retrieval.
        
        Args:
            query: Query text
            k: Number of results to return
            filter: Optional filter for the search
            alpha: Weight between dense and sparse scores
            
        Returns:
            List of hybrid search results
        """
        # Get dense results
        dense_results = await self.similarity_search(query, k=k*2, filter=filter)
        
        # Get sparse results (BM25 or similar)
        sparse_results = await self._sparse_search(query, k=k*2, filter=filter)
        
        # Combine results
        combined_results = await self._combine_search_results(
            dense_results, sparse_results, alpha=alpha
        )
        
        # Take top k
        return combined_results[:k]
    
    async def _sparse_search(
        self, 
        query: str, 
        k: int = 5, 
        filter: Dict[str, Any] = None
    ) -> List[SparseSearchResult]:
        """
        Perform sparse search (e.g., BM25).
        
        This is a simplified implementation. In a real system, you would use
        a dedicated sparse search engine like Elasticsearch.
        """
        # This is a placeholder. Implement with a real sparse search engine
        # For now, we'll just return empty results
        return []
    
    async def _combine_search_results(
        self,
        dense_results: List[VectorSearchResult],
        sparse_results: List[SparseSearchResult],
        alpha: float = 0.5
    ) -> List[HybridSearchResult]:
        """
        Combine dense and sparse search results.
        
        Args:
            dense_results: Results from vector search
            sparse_results: Results from sparse search
            alpha: Weight for dense vs sparse (0 = all sparse, 1 = all dense)
            
        Returns:
            Combined results
        """
        # Create lookup dictionaries
        dense_dict = {r.id: r for r in dense_results}
        sparse_dict = {r.id: r for r in sparse_results}
        
        # Get all unique IDs
        all_ids = set(dense_dict.keys()) | set(sparse_dict.keys())
        
        # Combine scores
        combined_results = []
        for id in all_ids:
            dense_score = dense_dict[id].score if id in dense_dict else 0.0
            sparse_score = sparse_dict[id].score if id in sparse_dict else 0.0
            
            # Normalize scores if needed
            
            # Combine scores
            combined_score = alpha * dense_score + (1 - alpha) * sparse_score
            
            # Get text and metadata from whichever result has it
            if id in dense_dict:
                text = dense_dict[id].text
                metadata = dense_dict[id].metadata
            else:
                text = sparse_dict[id].text
                metadata = sparse_dict[id].metadata
            
            combined_results.append(
                HybridSearchResult(
                    id=id,
                    text=text,
                    dense_score=dense_score,
                    sparse_score=sparse_score,
                    combined_score=combined_score,
                    metadata=metadata
                )
            )
        
        # Sort by combined score
        combined_results.sort(key=lambda x: x.combined_score, reverse=True)
        
        return combined_results
    
    def _convert_to_qdrant_filter(self, filter: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a generic filter to Qdrant filter format."""
        # This is a simplified implementation
        qdrant_filter = {"must": []}
        
        for field, value in filter.items():
            # Handle metadata fields
            if field.startswith("metadata."):
                field_path = field.split(".")
                field_name = ".".join(["metadata"] + field_path[1:])
                
                if isinstance(value, list):
                    qdrant_filter["must"].append({
                        "key": field_name,
                        "match": {"any": value}
                    })
                else:
                    qdrant_filter["must"].append({
                        "key": field_name,
                        "match": {"value": value}
                    })
            else:
                # Handle regular fields
                if isinstance(value, list):
                    qdrant_filter["must"].append({
                        "key": field,
                        "match": {"any": value}
                    })
                else:
                    qdrant_filter["must"].append({
                        "key": field,
                        "match": {"value": value}
                    })
        
        return qdrant_filter
    
    def _convert_to_milvus_filter(self, filter: Dict[str, Any]) -> str:
        """Convert a generic filter to Milvus filter expression."""
        # This is a simplified implementation
        expressions = []
        
        for field, value in filter.items():
            if field.startswith("metadata."):
                # We can't directly filter on nested fields in Milvus JSON type
                # Filtering would need to be done after retrieval
                continue
            
            if isinstance(value, list):
                expr = f"{field} in {json.dumps(value)}"
            else:
                expr = f"{field} == {json.dumps(value)}"
            
            expressions.append(expr)
        
        if not expressions:
            return None
        
        return " && ".join(expressions)
    
    def _matches_filter(self, metadata: Dict[str, Any], filter: Dict[str, Any]) -> bool:
        """Check if metadata matches a filter."""
        for field, value in filter.items():
            if field.startswith("metadata."):
                field_path = field.split(".")[1:]
                current = metadata
                
                # Navigate nested structure
                for path_part in field_path:
                    if path_part not in current:
                        return False
                    current = current[path_part]
                
                # Check value
                if isinstance(value, list):
                    if current not in value:
                        return False
                elif current != value:
                    return False
            else:
                # For non-metadata fields
                if field not in metadata:
                    return False
                
                if isinstance(value, list):
                    if metadata[field] not in value:
                        return False
                elif metadata[field] != value:
                    return False
        
        return True
    
    async def delete(self, ids: List[str]) -> bool:
        """Delete vectors by IDs."""
        if self.vector_db_type == "qdrant":
            self._client.delete(
                collection_name=self.collection_name,
                points_selector=self._qdrant_models.PointIdsList(
                    points=ids
                )
            )
        
        elif self.vector_db_type == "faiss":
            # FAISS doesn't support deletion directly
            # We would need to rebuild the index without the deleted vectors
            # This is a simplified implementation
            for id in ids:
                if id in self._faiss_ids:
                    idx = self._faiss_ids.index(id)
                    self._faiss_ids.pop(idx)
                    self._faiss_texts.pop(id, None)
                    self._faiss_metadata.pop(id, None)
        
        elif self.vector_db_type == "milvus":
            expr = f"id in {json.dumps(ids)}"
            self._client.delete(expr)
        
        # Update metrics
        self.metrics.total_vectors -= len(ids)
        self.metrics.last_updated = time.time()
        
        return True
    
    async def get_by_id(self, id: str) -> Optional[Dict[str, Any]]:
        """Get a vector by ID."""
        if self.vector_db_type == "qdrant":
            result = self._client.retrieve(
                collection_name=self.collection_name,
                ids=[id]
            )
            
            if not result:
                return None
            
            return {
                "id": id,
                "text": result[0].payload["text"],
                "metadata": result[0].payload.get("metadata", {})
            }
        
        elif self.vector_db_type == "faiss":
            if id not in self._faiss_ids:
                return None
            
            return {
                "id": id,
                "text": self._faiss_texts[id],
                "metadata": self._faiss_metadata[id]
            }
        
        elif self.vector_db_type == "milvus":
            self._client.load()
            result = self._client.query(
                expr=f'id == "{id}"',
                output_fields=["text", "metadata"]
            )
            
            if not result:
                return None
            
            return {
                "id": id,
                "text": result[0]["text"],
                "metadata": json.loads(result[0]["metadata"])
            }
    
    async def count(self) -> int:
        """Get the total number of vectors in the store."""
        if self.vector_db_type == "qdrant":
            result = self._client.get_collection(self.collection_name)
            return result.vectors_count
        
        elif self.vector_db_type == "faiss":
            return len(self._faiss_ids)
        
        elif self.vector_db_type == "milvus":
            return self._client.num_entities
    
    def get_metrics(self) -> VectorMetrics:
        """Get current metrics for the vector store."""
        return self.metrics


def init_vector_store():
    """Initialize the vector store during application startup."""
    global _vector_store
    _vector_store = VectorStoreService()
    logger.info(f"Initialized vector store: {_vector_store.vector_db_type}")
    return _vector_store


# Singleton instance
_vector_store = None

def get_vector_store() -> VectorStoreService:
    """Get the vector store service singleton."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStoreService()
    return _vector_store