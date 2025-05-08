"""
OpenAI embedding models
"""

import logging
import time
from typing import Dict, List, Any, Optional, Union

from .base import APIEmbeddingModelBase, EmbeddingError

logger = logging.getLogger(__name__)

class OpenAIEmbeddingModel(APIEmbeddingModelBase):
    """OpenAI API-based embedding model"""
    
    def _init_client(self) -> None:
        """Initialize OpenAI client"""
        try:
            import openai
            
            if not self.api_key:
                raise EmbeddingError("OpenAI API key is required")
            
            # Initialize client
            self.client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.api_base_url
            )
            
            logger.info(f"OpenAI client initialized for model {self.model_id}")
        except ImportError:
            raise EmbeddingError("openai package not installed. Install with: pip install openai")
    
    def embed(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for text
        
        Args:
            text: Text to embed
            
        Returns:
            Optional[List[float]]: Embedding vector or None if failed
        """
        if not self._initialized:
            if not self.initialize():
                return None
        
        # Handle empty text
        if not text.strip():
            # Return zero vector
            return [0.0] * self.dimensions
        
        try:
            # Handle token limit
            if len(text) > 8191:  # ~8k tokens for newer models
                logger.warning(f"Text too long ({len(text)} chars), truncating")
                text = text[:8191]
            
            # Call OpenAI API
            response = self.client.embeddings.create(
                model=self.model_id,
                input=text,
                encoding_format=self.options.get("encoding_format", "float")
            )
            
            # Extract embedding
            embedding = response.data[0].embedding
            
            return embedding
        except Exception as e:
            # Handle rate limiting
            if "rate limit" in str(e).lower():
                retry_after = 2  # Default retry after 2 seconds
                
                # Try to extract retry time from error
                error_str = str(e)
                if "retry after" in error_str.lower():
                    try:
                        retry_part = error_str.split("retry after")[1].split("s")[0].strip()
                        retry_after = int(retry_part)
                    except:
                        pass
                
                logger.warning(f"Rate limited by OpenAI, retrying after {retry_after}s")
                time.sleep(retry_after)
                
                # Retry once
                try:
                    response = self.client.embeddings.create(
                        model=self.model_id,
                        input=text,
                        encoding_format=self.options.get("encoding_format", "float")
                    )
                    
                    embedding = response.data[0].embedding
                    return embedding
                except Exception as retry_e:
                    logger.error(f"Retry failed: {str(retry_e)}")
                    return None
            else:
                logger.error(f"Error generating embedding: {str(e)}")
                return None
    
    def embed_batch(self, texts: List[str]) -> Optional[List[List[float]]]:
        """
        Generate embeddings for multiple texts
        
        Args:
            texts: List of texts to embed
            
        Returns:
            Optional[List[List[float]]]: List of embedding vectors or None if failed
        """
        if not self._initialized:
            if not self.initialize():
                return None
        
        if not texts:
            return []
        
        try:
            # Handle token limit and filter empty texts
            processed_texts = []
            for text in texts:
                if not text.strip():
                    processed_texts.append("")
                elif len(text) > 8191:
                    processed_texts.append(text[:8191])
                else:
                    processed_texts.append(text)
            
            # Call OpenAI API
            response = self.client.embeddings.create(
                model=self.model_id,
                input=processed_texts,
                encoding_format=self.options.get("encoding_format", "float")
            )
            
            # Extract embeddings (ensuring they're in the same order as input)
            embeddings_dict = {item.index: item.embedding for item in response.data}
            embeddings = [embeddings_dict.get(i, [0.0] * self.dimensions) for i in range(len(texts))]
            
            return embeddings
        except Exception as e:
            # Handle rate limiting
            if "rate limit" in str(e).lower():
                retry_after = 5  # Default retry after 5 seconds for batch
                
                logger.warning(f"Rate limited by OpenAI, retrying batch after {retry_after}s")
                time.sleep(retry_after)
                
                # Process in smaller batches
                batch_size = max(1, len(texts) // 2)
                logger.info(f"Retrying with smaller batch size: {batch_size}")
                
                try:
                    # Process first half
                    first_half = texts[:batch_size]
                    first_response = self.client.embeddings.create(
                        model=self.model_id,
                        input=first_half,
                        encoding_format=self.options.get("encoding_format", "float")
                    )
                    
                    # Process second half
                    second_half = texts[batch_size:]
                    if second_half:
                        time.sleep(1)  # Brief pause between requests
                        second_response = self.client.embeddings.create(
                            model=self.model_id,
                            input=second_half,
                            encoding_format=self.options.get("encoding_format", "float")
                        )
                        
                        # Combine results
                        first_embeddings = [item.embedding for item in first_response.data]
                        second_embeddings = [item.embedding for item in second_response.data]
                        return first_embeddings + second_embeddings
                    else:
                        # Only first half
                        return [item.embedding for item in first_response.data]
                except Exception as retry_e:
                    logger.error(f"Batch retry failed: {str(retry_e)}")
                    return None
            else:
                logger.error(f"Error generating batch embeddings: {str(e)}")
                return None