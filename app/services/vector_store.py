from typing import Dict, List, Optional, Union, Any
import numpy as np
import logging
import time
import os
import faiss
import pickle
import torch
import asyncio
from pydantic import BaseModel

from app.core.config import settings
from app.models.model_manager import get_model_manager
from app.utils.metrics import get_retrieval_metrics

logger = logging.getLogger(__name__)
retrieval_metrics = get_retrieval_metrics()

class SearchResult(BaseModel):
    """Class representing a search result."""
    id: str
    text: str
    score: float
    metadata: Dict[str, Any] = {}


class VectorStore:
    """
    Vector storage and search service using FAISS.
    
    Manages embedding vectors for documents and provides
    similarity search functionality.
    """
    
    def __init__(self):
        """Initialize the vector store."""
        self.index_path = os.path.join(settings.storage_dir, "vector_index")
        self.metadata_path = os.path.join(settings.storage_dir, "vector_metadata.pkl")
        
        # Create storage directory if it doesn't exist
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        
        # Initialize empty index and metadata
        self.index = None
        self.metadata: Dict[str, Dict[str, Any]] = {}
        self.id_to_index: Dict[str, int] = {}
        self.index_to_id: Dict[int, str] = {}
        self.initialized = False
        
        # Default embedding dimension
        self.dimension = 384  # Default, will be determined by the model
        
        # Lock for thread safety during updates
        self._lock = asyncio.Lock()
    
    async def initialize(self) -> None:
        """
        Initialize the vector store by loading index and metadata.
        
        This method will try to load existing index and metadata from disk,
        or create a new index if none exists.
        """
        async with self._lock:
            if self.initialized:
                return
            
            logger.info("Initializing vector store")
            start_time = time.time()
            
            # Try loading existing index and metadata
            try:
                if os.path.exists(self.index_path) and os.path.exists(self.metadata_path):
                    # Load index
                    self.index = faiss.read_index(self.index_path)
                    
                    # Load metadata
                    with open(self.metadata_path, 'rb') as f:
                        loaded_data = pickle.load(f)
                        self.metadata = loaded_data.get('metadata', {})
                        self.id_to_index = loaded_data.get('id_to_index', {})
                        self.index_to_id = loaded_data.get('index_to_id', {})
                        self.dimension = loaded_data.get('dimension', 384)
                    
                    logger.info(f"Loaded existing index with {self.index.ntotal} vectors")
                else:
                    # Get embedding dimension from model
                    model_manager = get_model_manager()
                    model_info = model_manager.get_model()
                    if model_info:
                        self.dimension = model_info.dimension
                    
                    # Create a new index
                    self.index = faiss.IndexFlatL2(self.dimension)
                    logger.info(f"Created new index with dimension {self.dimension}")
            
            except Exception as e:
                logger.error(f"Error loading index: {str(e)}")
                # Create a fallback index
                self.index = faiss.IndexFlatL2(self.dimension)
                logger.info(f"Created fallback index with dimension {self.dimension}")
            
            self.initialized = True
            logger.info(f"Vector store initialized in {time.time() - start_time:.2f}s")
    
    async def add_documents(
        self,
        documents: List[Dict[str, Any]],
        embedding_model: Optional[str] = None
    ) -> List[str]:
        """
        Add documents to the vector store.
        
        Each document should be a dictionary with at least 'id' and 'text' keys.
        Optional metadata can be included as well.
        
        Args:
            documents: List of document dictionaries
            embedding_model: Optional name of the embedding model to use
            
        Returns:
            List of document IDs that were added
        """
        if not documents:
            return []
        
        # Ensure store is initialized
        await self.initialize()
        
        # Extract texts for embedding
        texts = [doc['text'] for doc in documents]
        
        # Generate embeddings
        embeddings = await self.embed_documents(texts, model_name=embedding_model)
        
        # Add to index and metadata
        async with self._lock:
            # Current index size
            start_index = self.index.ntotal
            
            # Add to index
            faiss.normalize_L2(embeddings)  # Normalize for cosine similarity
            self.index.add(embeddings)
            
            # Add metadata and mapping
            document_ids = []
            for i, doc in enumerate(documents):
                doc_id = doc['id']
                index_id = start_index + i
                
                # Store ID mappings
                self.id_to_index[doc_id] = index_id
                self.index_to_id[index_id] = doc_id
                
                # Store metadata
                self.metadata[doc_id] = {
                    'text': doc['text'],
                    'model': embedding_model,
                    'added_at': time.time()
                }
                
                # Add any additional metadata
                if 'metadata' in doc:
                    self.metadata[doc_id].update(doc['metadata'])
                
                document_ids.append(doc_id)
            
            # Save updated index and metadata
            await self._save_index()
            
            logger.info(f"Added {len(documents)} documents to vector store")
            
            return document_ids
    
    async def similarity_search(
        self,
        query: str,
        k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        embedding_model: Optional[str] = None,
        **kwargs
    ) -> List[SearchResult]:
        """
        Perform similarity search for a query.
        
        Args:
            query: The search query
            k: Number of results to return
            filters: Optional metadata filters
            embedding_model: Optional name of the embedding model to use
            **kwargs: Additional arguments
            
        Returns:
            List of search results
        """
        # Track search with metrics
        start_time = time.time()
        method = "vector"
        if "track_stage" in kwargs and callable(kwargs["track_stage"]):
            track_stage = kwargs["track_stage"]
            track_stage("vector_search", start=True)
        
        # Ensure store is initialized
        await self.initialize()
        
        if self.index.ntotal == 0:
            logger.warning("Vector store is empty")
            return []
        
        try:
            # Generate query embedding
            query_embedding = await self.embed_query(query, model_name=embedding_model)
            
            # Normalize for cosine similarity
            faiss.normalize_L2(query_embedding)
            
            # Filter document IDs if filters provided
            filtered_indices = None
            if filters:
                filtered_ids = self._apply_filters(filters)
                if not filtered_ids:
                    return []  # No documents match filters
                
                # Map IDs to indices
                filtered_indices = [self.id_to_index[doc_id] for doc_id in filtered_ids]
            
            # Create subset index if filtering
            search_index = self.index
            if filtered_indices:
                search_index = faiss.IndexFlatL2(self.dimension)
                vecs = np.zeros((len(filtered_indices), self.dimension), dtype=np.float32)
                
                for i, idx in enumerate(filtered_indices):
                    faiss.index_search_index_by_id(self.index, idx, vecs, i)
                
                search_index.add(vecs)
            
            # Perform search
            scores, indices = search_index.search(query_embedding, k)
            
            # Map search results to document IDs
            results = []
            for i in range(min(len(indices[0]), k)):
                idx = indices[0][i]
                score = float(scores[0][i])
                
                # Skip if score is too low (no good matches)
                if score < 0:
                    continue
                
                # Get document ID from index
                if filtered_indices:
                    # If using subset index, we need to map back to original indices
                    doc_id = self.index_to_id.get(filtered_indices[idx])
                else:
                    doc_id = self.index_to_id.get(idx)
                
                if not doc_id or doc_id not in self.metadata:
                    continue
                
                # Convert cosine distance to similarity
                similarity_score = 1.0 - score / 2.0
                
                # Create search result
                result = SearchResult(
                    id=doc_id,
                    text=self.metadata[doc_id]['text'],
                    score=similarity_score,
                    metadata=self.metadata[doc_id]
                )
                results.append(result)
            
            # Record metrics
            search_time = time.time() - start_time
            retrieval_metrics.record_results(method, len(results))
            if "track_stage" in kwargs and callable(kwargs["track_stage"]):
                track_stage("vector_search", start=False)
            
            return results
            
        except Exception as e:
            logger.error(f"Error during similarity search: {str(e)}")
            if "track_stage" in kwargs and callable(kwargs["track_stage"]):
                track_stage("vector_search", start=False)
            return []
    
    async def delete_documents(self, document_ids: List[str]) -> int:
        """
        Delete documents from the vector store.
        
        Args:
            document_ids: List of document IDs to delete
            
        Returns:
            Number of documents deleted
        """
        if not document_ids:
            return 0
        
        # Ensure store is initialized
        await self.initialize()
        
        async with self._lock:
            # FAISS doesn't support direct deletion, we need to rebuild the index
            if self.index.ntotal == 0:
                return 0
            
            # Get existing IDs
            existing_ids = set(self.id_to_index.keys())
            ids_to_delete = set(document_ids) & existing_ids
            
            if not ids_to_delete:
                return 0
            
            # Collect vectors to keep
            keep_ids = existing_ids - ids_to_delete
            keep_indices = [self.id_to_index[doc_id] for doc_id in keep_ids]
            
            # Create a new index
            new_index = faiss.IndexFlatL2(self.dimension)
            
            if keep_indices:
                # Extract vectors to keep
                vecs = np.zeros((len(keep_indices), self.dimension), dtype=np.float32)
                for i, idx in enumerate(keep_indices):
                    faiss.index_get_vector(self.index, idx, vecs[i])
                
                # Add vectors to new index
                new_index.add(vecs)
            
            # Update id mappings
            new_id_to_index = {}
            new_index_to_id = {}
            
            for i, doc_id in enumerate(keep_ids):
                new_id_to_index[doc_id] = i
                new_index_to_id[i] = doc_id
            
            # Delete metadata
            for doc_id in ids_to_delete:
                if doc_id in self.metadata:
                    del self.metadata[doc_id]
            
            # Replace old index and mappings
            self.index = new_index
            self.id_to_index = new_id_to_index
            self.index_to_id = new_index_to_id
            
            # Save updated index and metadata
            await self._save_index()
            
            deleted_count = len(ids_to_delete)
            logger.info(f"Deleted {deleted_count} documents from vector store")
            
            return deleted_count
    
    async def embed_documents(
        self,
        texts: List[str],
        model_name: Optional[str] = None
    ) -> np.ndarray:
        """Embed documents using the model manager."""
        if not texts:
            return np.array([])
        
        # Get model manager
        model_manager = get_model_manager()
        
        # Generate embeddings
        return await model_manager.encode(texts, model_name=model_name)
    
    async def embed_query(
        self,
        query: str,
        model_name: Optional[str] = None
    ) -> np.ndarray:
        """Embed a query using the model manager."""
        # Get model manager
        model_manager = get_model_manager()
        
        # Generate embedding
        return await model_manager.encode([query], model_name=model_name)
    
    def _apply_filters(self, filters: Dict[str, Any]) -> List[str]:
        """
        Apply metadata filters to get matching document IDs.
        
        Args:
            filters: Dictionary of metadata filters
            
        Returns:
            List of document IDs that match the filters
        """
        if not filters:
            return list(self.metadata.keys())
        
        matching_ids = []
        
        for doc_id, metadata in self.metadata.items():
            matches = True
            
            for key, value in filters.items():
                # Handle special operators in key
                if key.endswith('__gt'):
                    field = key[:-4]
                    if field not in metadata or metadata[field] <= value:
                        matches = False
                        break
                elif key.endswith('__lt'):
                    field = key[:-4]
                    if field not in metadata or metadata[field] >= value:
                        matches = False
                        break
                elif key.endswith('__gte'):
                    field = key[:-5]
                    if field not in metadata or metadata[field] < value:
                        matches = False
                        break
                elif key.endswith('__lte'):
                    field = key[:-5]
                    if field not in metadata or metadata[field] > value:
                        matches = False
                        break
                elif key.endswith('__in'):
                    field = key[:-4]
                    if field not in metadata or metadata[field] not in value:
                        matches = False
                        break
                else:
                    # Exact match
                    if key not in metadata or metadata[key] != value:
                        matches = False
                        break
            
            if matches:
                matching_ids.append(doc_id)
        
        return matching_ids
    
    async def _save_index(self) -> None:
        """Save index and metadata to disk."""
        try:
            # Save index
            faiss.write_index(self.index, self.index_path)
            
            # Save metadata
            with open(self.metadata_path, 'wb') as f:
                pickle.dump({
                    'metadata': self.metadata,
                    'id_to_index': self.id_to_index,
                    'index_to_id': self.index_to_id,
                    'dimension': self.dimension
                }, f)
            
            logger.debug("Vector store saved to disk")
        except Exception as e:
            logger.error(f"Error saving vector store: {str(e)}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store."""
        await self.initialize()
        
        return {
            "total_vectors": self.index.ntotal,
            "dimension": self.dimension,
            "total_documents": len(self.metadata),
            "index_type": type(self.index).__name__
        }


# Create a singleton instance
_vector_store = None

def get_vector_store() -> VectorStore:
    """Get the vector store singleton instance."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store