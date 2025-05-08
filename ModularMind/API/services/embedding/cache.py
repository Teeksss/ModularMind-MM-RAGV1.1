"""
Caching system for embeddings
"""

import os
import time
import json
import pickle
import logging
from typing import Dict, List, Any, Optional, Union, Tuple
from collections import OrderedDict

logger = logging.getLogger(__name__)

class EmbeddingCache:
    """
    Cache for storing embeddings to avoid redundant API calls.
    Implements a simple LRU (Least Recently Used) cache.
    """
    
    def __init__(
        self, 
        max_size: int = 10000, 
        ttl: int = 3600,
        persistent: bool = False,
        persistent_path: Optional[str] = None
    ):
        """
        Initialize embedding cache
        
        Args:
            max_size: Maximum number of cached embeddings
            ttl: Time to live in seconds (0 for no expiry)
            persistent: Whether to save cache to disk
            persistent_path: Path to save cache to
        """
        self.max_size = max_size
        self.ttl = ttl
        self.persistent = persistent
        self.persistent_path = persistent_path
        
        # Cache structure: {key: (embedding, timestamp)}
        self.cache: OrderedDict[str, Tuple[List[float], float]] = OrderedDict()
        
        # Load cache from disk if persistent
        if self.persistent and self.persistent_path:
            self._load_cache()
    
    def get(self, key: str) -> Optional[List[float]]:
        """
        Get embedding from cache
        
        Args:
            key: Cache key
            
        Returns:
            Optional[List[float]]: Cached embedding or None if not found or expired
        """
        if key not in self.cache:
            return None
        
        # Get embedding and timestamp
        embedding, timestamp = self.cache[key]
        
        # Check if expired
        if self.ttl > 0 and time.time() - timestamp > self.ttl:
            # Remove expired item
            del self.cache[key]
            return None
        
        # Move to end (most recently used)
        self.cache.move_to_end(key)
        
        return embedding
    
    def set(self, key: str, embedding: List[float]) -> None:
        """
        Set embedding in cache
        
        Args:
            key: Cache key
            embedding: Embedding vector
        """
        # Remove oldest item if at capacity
        if len(self.cache) >= self.max_size and key not in self.cache:
            self.cache.popitem(last=False)
        
        # Add or update item
        self.cache[key] = (embedding, time.time())
        
        # Save to disk if persistent
        if self.persistent and self.persistent_path:
            self._save_cache()
    
    def clear(self) -> None:
        """Clear the cache"""
        self.cache.clear()
        
        # Remove persistent cache file if exists
        if self.persistent and self.persistent_path:
            cache_file = os.path.join(self.persistent_path, "embedding_cache.pkl")
            if os.path.exists(cache_file):
                try:
                    os.remove(cache_file)
                except Exception as e:
                    logger.error(f"Error removing cache file: {str(e)}")
    
    def _save_cache(self) -> None:
        """Save cache to disk"""
        if not self.persistent_path:
            return
        
        try:
            # Create directory if it doesn't exist
            os.makedirs(self.persistent_path, exist_ok=True)
            
            # Save cache to file
            cache_file = os.path.join(self.persistent_path, "embedding_cache.pkl")
            with open(cache_file, "wb") as f:
                pickle.dump(dict(self.cache), f)
        except Exception as e:
            logger.error(f"Error saving cache to disk: {str(e)}")
    
    def _load_cache(self) -> None:
        """Load cache from disk"""
        if not self.persistent_path:
            return
        
        try:
            # Check if cache file exists
            cache_file = os.path.join(self.persistent_path, "embedding_cache.pkl")
            if not os.path.exists(cache_file):
                return
            
            # Load cache from file
            with open(cache_file, "rb") as f:
                loaded_cache = pickle.load(f)
            
            # Create ordered dict and apply LRU eviction if needed
            self.cache = OrderedDict()
            
            # Sort by timestamp (oldest first)
            sorted_items = sorted(loaded_cache.items(), key=lambda x: x[1][1])
            
            # Add items (up to max_size)
            for key, (embedding, timestamp) in sorted_items[-self.max_size:]:
                # Skip expired items
                if self.ttl > 0 and time.time() - timestamp > self.ttl:
                    continue
                
                self.cache[key] = (embedding, timestamp)
            
            logger.info(f"Loaded {len(self.cache)} embeddings from persistent cache")
        except Exception as e:
            logger.error(f"Error loading cache from disk: {str(e)}")