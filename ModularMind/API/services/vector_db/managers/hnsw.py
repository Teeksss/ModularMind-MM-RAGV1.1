"""
HNSW index manager for vector storage
"""
import os
import logging
import numpy as np
from typing import Dict, Any, List, Optional, Tuple, Union, Set
import time

from ..base import BaseIndexManager
from ..config import HNSWConfig, DistanceMetric
from ..utils import normalize_vector, convert_distance_to_similarity
from ..metrics import compute_similarity

logger = logging.getLogger(__name__)

class HNSWIndexManager(BaseIndexManager):
    """
    HNSW (Hierarchical Navigable Small World) index manager.
    
    This implementation uses the hnswlib library for efficient approximate nearest
    neighbor search with HNSW algorithm.
    """
    
    def __init__(self, config: Union[Dict[str, Any], HNSWConfig]):
        """
        Initialize HNSW index manager
        
        Args:
            config: HNSW configuration (either as dict or HNSWConfig object)
        """
        if isinstance(config, dict):
            self.config = HNSWConfig.from_dict(config)
        else:
            self.config = config
            
        self.index = None
        self.id_to_docid = {}  # Maps internal index IDs to document IDs
        self.docid_to_id = {}  # Maps document IDs to internal index IDs
        self.next_id = 0
        self._initialized = False
        
    def initialize(self) -> bool:
        """
        Initialize the HNSW index
        
        Returns:
            bool: True if initialization successful
        """
        try:
            import hnswlib
            
            # Create HNSW index
            space = self._get_space_name()
            self.index = hnswlib.Index(space=space, dim=self.config.dimensions)
            
            max_elements = self.config.max_elements or 100000  # Default to 100K if not specified
            
            self.index.init_index(
                max_elements=max_elements,
                ef_construction=self.config.ef_construction,
                M=self.config.M
            )
            
            # Set search parameters
            self.index.set_ef(self.config.ef_search)
            
            self._initialized = True
            logger.info(f"HNSW index initialized with dim={self.config.dimensions}, "
                       f"metric={self.config.metric.value}")
            return True
            
        except ImportError:
            logger.error("hnswlib not installed. Install with: pip install hnswlib")
            return False
        except Exception as e:
            logger.error(f"Error initializing HNSW index: {str(e)}")
            return False
    
    def _get_space_name(self) -> str:
        """
        Convert metric enum to hnswlib space name
        
        Returns:
            str: hnswlib space name
        """
        if self.config.metric == DistanceMetric.COSINE:
            return "cosine"
        elif self.config.metric == DistanceMetric.EUCLIDEAN:
            return "l2"
        elif self.config.metric == DistanceMetric.DOT:
            return "ip"  # Inner product
        else:
            # HNSW doesn't support Manhattan, fall back to L2
            logger.warning("HNSW doesn't support Manhattan distance, using L2 instead")
            return "l2"
    
    def add_item(self, vector: List[float], doc_id: str) -> bool:
        """
        Add a vector to the index
        
        Args:
            vector: Vector to add
            doc_id: Document ID to associate with this vector
            
        Returns:
            bool: True if addition successful
        """
        if not self._initialized:
            if not self.initialize():
                return False
                
        try:
            # Convert vector to numpy array
            vector_np = np.array(vector, dtype=np.float32)
            
            # Normalize vector if using cosine similarity
            if self.config.metric == DistanceMetric.COSINE:
                vector_np = normalize_vector(vector_np)
            
            # Check if document already exists
            if doc_id in self.docid_to_id:
                # Update existing item
                index_id = self.docid_to_id[doc_id]
                self.index.set_items(np.array([index_id]), np.array([vector_np]))
            else:
                # Add new item
                index_id = self.next_id
                self.next_id += 1
                
                self.index.add_items(vector_np, np.array([index_id]))
                
                # Update mappings
                self.id_to_docid[index_id] = doc_id
                self.docid_to_id[doc_id] = index_id
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding item to HNSW index: {str(e)}")
            return False
    
    def add_items_batch(self, vectors: List[List[float]], doc_ids: List[str]) -> bool:
        """
        Add multiple vectors to the index in batch
        
        Args:
            vectors: List of vectors to add
            doc_ids: List of document IDs to associate with vectors
            
        Returns:
            bool: True if addition successful
        """
        if not self._initialized:
            if not self.initialize():
                return False
        
        if len(vectors) != len(doc_ids):
            logger.error(f"Mismatch in batch sizes: {len(vectors)} vectors vs {len(doc_ids)} doc_ids")
            return False
            
        try:
            # Convert vectors to numpy array
            vectors_np = np.array(vectors, dtype=np.float32)
            
            # Normalize vectors if using cosine similarity
            if self.config.metric == DistanceMetric.COSINE:
                for i in range(vectors_np.shape[0]):
                    vectors_np[i] = normalize_vector(vectors_np[i])
            
            # Process items in batch
            new_ids = []
            new_vectors = []
            update_ids = []
            update_vectors = []
            
            for i, doc_id in enumerate(doc_ids):
                if doc_id in self.docid_to_id:
                    # Update existing item
                    index_id = self.docid_to_id[doc_id]
                    update_ids.append(index_id)
                    update_vectors.append(vectors_np[i])
                else:
                    # Add new item
                    index_id = self.next_id
                    self.next_id += 1
                    
                    new_ids.append(index_id)
                    new_vectors.append(vectors_np[i])
                    
                    # Update mappings
                    self.id_to_docid[index_id] = doc_id
                    self.docid_to_id[doc_id] = index_id
            
            # Add new items
            if new_ids:
                new_ids_np = np.array(new_ids)
                new_vectors_np = np.array(new_vectors)
                self.index.add_items(new_vectors_np, new_ids_np)
            
            # Update existing items
            if update_ids:
                update_ids_np = np.array(update_ids)
                update_vectors_np = np.array(update_vectors)
                self.index.set_items(update_ids_np, update_vectors_np)
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding items in batch to HNSW index: {str(e)}")
            return False
    
    def search(self, query_vector: List[float], top_k: int = 10, 
              min_score: Optional[float] = None) -> List[Tuple[str, float]]:
        """
        Search for similar vectors in the index
        
        Args:
            query_vector: Query vector
            top_k: Number of results to return
            min_score: Minimum similarity score (0-1 range)
            
        Returns:
            List of (doc_id, score) tuples
        """
        if not self._initialized or len(self.id_to_docid) == 0:
            logger.warning("HNSW index not initialized or empty")
            return []
            
        try:
            # Convert query vector to numpy array
            query_np = np.array(query_vector, dtype=np.float32)
            
            # Normalize query if using cosine similarity
            if self.config.metric == DistanceMetric.COSINE:
                query_np = normalize_vector(query_np)
            
            # Perform search
            index_ids, distances = self.index.knn_query(query_np, k=min(top_k, len(self.id_to_docid)))
            
            # Flatten results
            index_ids = index_ids[0]
            distances = distances[0]
            
            # Convert distances to similarity scores (0-1 range where 1 is most similar)
            scores = []
            for dist in distances:
                score = convert_distance_to_similarity(dist, self.config.metric)
                scores.append(score)
            
            # Create result list of (doc_id, score) tuples
            results = []
            for i, index_id in enumerate(index_ids):
                doc_id = self.id_to_docid.get(index_id)
                if doc_id is None:
                    continue
                    
                score = scores[i]
                
                # Apply minimum score filter if provided
                if min_score is not None and score < min_score:
                    continue
                    
                results.append((doc_id, score))
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching HNSW index: {str(e)}")
            return []
    
    def delete_item(self, doc_id: str) -> bool:
        """
        Delete a vector from the index
        
        Args:
            doc_id: Document ID to delete
            
        Returns:
            bool: True if deletion successful
        """
        if not self._initialized:
            logger.warning("HNSW index not initialized")
            return False
            
        try:
            if doc_id not in self.docid_to_id:
                logger.warning(f"Document ID {doc_id} not found in index")
                return False
                
            # Get internal index ID
            index_id = self.docid_to_id[doc_id]
            
            # HNSW doesn't support direct deletion, mark for re-use
            # Future implementations could rebuild the index periodically
            
            # Remove from mappings
            del self.docid_to_id[doc_id]
            del self.id_to_docid[index_id]
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting item from HNSW index: {str(e)}")
            return False
    
    def save(self, path: str) -> bool:
        """
        Save the index to disk
        
        Args:
            path: Directory path to save the index
            
        Returns:
            bool: True if save successful
        """
        if not self._initialized:
            logger.warning("HNSW index not initialized")
            return False
            
        try:
            import json
            
            # Create directory if it doesn't exist
            os.makedirs(path, exist_ok=True)
            
            # Save HNSW index
            index_path = os.path.join(path, "hnsw_index.bin")
            self.index.save_index(index_path)
            
            # Save mappings
            mappings_path = os.path.join(path, "hnsw_mappings.json")
            
            # Convert keys to strings for JSON serialization
            id_to_docid_str = {str(k): v for k, v in self.id_to_docid.items()}
            
            mappings = {
                "id_to_docid": id_to_docid_str,
                "next_id": self.next_id
            }
            
            with open(mappings_path, "w") as f:
                json.dump(mappings, f)
            
            # Save config
            config_path = os.path.join(path, "hnsw_config.json")
            with open(config_path, "w") as f:
                json.dump(self.config.to_dict(), f)
            
            logger.info(f"HNSW index saved to {path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving HNSW index: {str(e)}")
            return False
    
    def load(self, path: str) -> bool:
        """
        Load the index from disk
        
        Args:
            path: Directory path to load the index from
            
        Returns:
            bool: True if load successful
        """
        try:
            import hnswlib
            import json
            
            # Check if files exist
            index_path = os.path.join(path, "hnsw_index.bin")
            mappings_path = os.path.join(path, "hnsw_mappings.json")
            config_path = os.path.join(path, "hnsw_config.json")
            
            if not os.path.exists(index_path) or not os.path.exists(mappings_path):
                logger.error(f"HNSW index files not found at {path}")
                return False
            
            # Load config if it exists
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    config_dict = json.load(f)
                    self.config = HNSWConfig.from_dict(config_dict)
            
            # Initialize empty index
            if not self._initialized:
                self.initialize()
            
            # Load HNSW index
            space = self._get_space_name()
            self.index = hnswlib.Index(space=space, dim=self.config.dimensions)
            self.index.load_index(index_path)
            self.index.set_ef(self.config.ef_search)
            
            # Load mappings
            with open(mappings_path, "r") as f:
                mappings = json.load(f)
            
            # Convert string keys back to integers
            self.id_to_docid = {int(k): v for k, v in mappings["id_to_docid"].items()}
            self.next_id = mappings["next_id"]
            
            # Rebuild docid_to_id mapping
            self.docid_to_id = {v: int(k) for k, v in mappings["id_to_docid"].items()}
            
            self._initialized = True
            logger.info(f"HNSW index loaded from {path}")
            return True
            
        except ImportError:
            logger.error("hnswlib not installed. Install with: pip install hnswlib")
            return False
        except Exception as e:
            logger.error(f"Error loading HNSW index: {str(e)}")
            return False