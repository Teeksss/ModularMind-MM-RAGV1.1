import logging
from typing import Dict, List, Optional, Set, Tuple, Union, Any
import asyncio
import time

from app.services.language_detection import get_language_detector, get_text_preprocessor
from app.models.model_manager import get_model_manager
from app.services.retrievers.base import BaseRetriever, SearchResult
from app.services.retrievers.hybrid_retriever import HybridRetriever
from app.core.config import settings
from app.services.translation import get_translation_service

logger = logging.getLogger(__name__)


class MultilingualRetriever:
    """
    Retrieval system that supports queries in multiple languages.
    
    Can detect query language, apply appropriate preprocessing,
    and use language-specific embeddings for retrieval.
    """
    
    def __init__(
        self,
        base_retriever: Optional[BaseRetriever] = None,
        translator_enabled: bool = False,
        default_language: str = "en"
    ):
        """
        Initialize the multilingual retriever.
        
        Args:
            base_retriever: Base retriever to use (optional)
            translator_enabled: Whether to enable translation (experimental)
            default_language: Default language for fallback
        """
        self.base_retriever = base_retriever
        self.translator_enabled = translator_enabled
        self.default_language = default_language
        self.language_detector = get_language_detector()
        self.text_preprocessor = get_text_preprocessor()
        self.model_manager = get_model_manager()
        
        # Initialize translation service if enabled
        self.translation_service = get_translation_service() if self.translator_enabled else None
        
        # Language-specific embedding models
        self.language_models = {
            'en': settings.default_embedding_model,
            'multi': 'paraphrase-multilingual-MiniLM-L12-v2',  # Default multilingual model
            # Language-specific models (to be added if available)
            'tr': 'bge-small-tr',  # Turkish model example
            'de': 'sentence-transformers/paraphrase-multilingual-mpnet-base-v2',
            'fr': 'sentence-transformers/paraphrase-multilingual-mpnet-base-v2',
            'es': 'sentence-transformers/paraphrase-multilingual-mpnet-base-v2',
            'zh': 'sentence-transformers/paraphrase-multilingual-mpnet-base-v2',
            'ja': 'sentence-transformers/paraphrase-multilingual-mpnet-base-v2',
        }
        
        # Load language-specific models from config if available
        lang_models = getattr(settings, "language_embedding_models", {})
        if lang_models:
            self.language_models.update(lang_models)
    
    async def initialize(self) -> None:
        """Initialize the multilingual retriever."""
        # Initialize base retriever if not provided
        if not self.base_retriever:
            self.base_retriever = HybridRetriever()
            await self.base_retriever.initialize()
        
        logger.info("Multilingual retriever initialized")
    
    async def search(
        self,
        query: str,
        k: int = 5,
        language: Optional[str] = None,
        detect_language: bool = True,
        filters: Optional[Dict[str, Any]] = None,
        return_language: bool = True,
        preprocess_query: bool = True,
        **kwargs
    ) -> Union[List[SearchResult], Tuple[List[SearchResult], Dict[str, Any]]]:
        """
        Search for documents in multiple languages.
        
        Args:
            query: The search query
            k: Number of results to return
            language: Query language (if None, will be detected)
            detect_language: Whether to perform language detection
            filters: Additional filters for search
            return_language: Whether to return language info in metadata
            preprocess_query: Whether to preprocess the query
            **kwargs: Additional arguments to pass to the base retriever
            
        Returns:
            List of search results or tuple of results and metadata
        """
        start_time = time.time()
        metadata = {}
        
        # Detect language if not provided
        detected_language = None
        if detect_language and not language:
            detected_language = await self.language_detector.detect_language(query)
            language = detected_language
            logger.debug(f"Detected query language: {language}")
            
            if return_language:
                metadata["detected_language"] = language
                metadata["language_name"] = self.language_detector.get_language_name(language)
        
        # Use default language if still None
        if not language:
            language = self.default_language
        
        # Preprocess query if requested
        if preprocess_query:
            processed_query = await self.text_preprocessor.preprocess(
                text=query,
                language=language,
                remove_stopwords=False  # Usually better to keep stopwords for embeddings
            )
            
            if return_language and processed_query != query:
                metadata["processed_query"] = processed_query
        else:
            processed_query = query
        
        # Select appropriate embedding model based on language
        model_name = self._get_embedding_model_for_language(language)
        
        if return_language and model_name:
            metadata["embedding_model"] = model_name
        
        # Translate query if enabled and language is different from default
        translated_query = None
        if self.translator_enabled and language != self.default_language and self.translation_service:
            try:
                translated_query = await self.translation_service.translate(
                    text=processed_query,
                    source_language=language,
                    target_language=self.default_language
                )
                
                if return_language:
                    metadata["translated_query"] = translated_query
                    
            except Exception as e:
                logger.error(f"Translation error: {str(e)}")
        
        # Prepare additional search attributes
        search_kwargs = kwargs.copy()
        if model_name:
            search_kwargs["embedding_model"] = model_name
        
        # Add language filter if available
        if language and filters:
            language_filters = filters.copy()
            # Add language to filters if metadata includes language
            if "language" not in language_filters and "metadata" in language_filters:
                language_filters["metadata"]["language"] = language
            filters = language_filters
        
        # Run searches in parallel if translation is used
        results = []
        if translated_query:
            # Original language search
            original_search_task = asyncio.create_task(
                self.base_retriever.search(
                    query=processed_query,
                    k=k,
                    filters=filters,
                    **search_kwargs
                )
            )
            
            # Get results from the default language model for translated query
            default_model = self.language_models.get(self.default_language)
            translated_search_kwargs = search_kwargs.copy()
            if default_model:
                translated_search_kwargs["embedding_model"] = default_model
            
            # Translated query search
            translated_search_task = asyncio.create_task(
                self.base_retriever.search(
                    query=translated_query,
                    k=k,
                    filters=filters,
                    **translated_search_kwargs
                )
            )
            
            # Await both searches
            original_results, translated_results = await asyncio.gather(
                original_search_task,
                translated_search_task
            )
            
            # Merge results, removing duplicates and taking the best score
            results = self._merge_results(original_results, translated_results)
            
            # Record translation info in metadata
            if return_language:
                metadata["used_translation"] = True
                metadata["original_results_count"] = len(original_results)
                metadata["translated_results_count"] = len(translated_results)
                metadata["merged_results_count"] = len(results)
        else:
            # Single language search
            results = await self.base_retriever.search(
                query=processed_query,
                k=k,
                filters=filters,
                **search_kwargs
            )
        
        # Record timing
        end_time = time.time()
        execution_time = end_time - start_time
        
        if return_language:
            metadata["execution_time"] = execution_time
            metadata["result_count"] = len(results)
            
            # Return results with metadata
            return results, metadata
        
        # Return just the results
        return results
    
    def _get_embedding_model_for_language(self, language: str) -> Optional[str]:
        """
        Get the appropriate embedding model for a language.
        
        Args:
            language: ISO 639-1 language code
            
        Returns:
            str or None: Name of the embedding model to use
        """
        # Check for language-specific model
        if language in self.language_models:
            return self.language_models[language]
        
        # Fallback to multilingual model
        if "multi" in self.language_models:
            return self.language_models["multi"]
        
        # Fallback to default model
        return self.language_models.get(self.default_language)
    
    def _merge_results(
        self,
        results1: List[SearchResult],
        results2: List[SearchResult],
        score_factor: float = 0.9
    ) -> List[SearchResult]:
        """
        Merge two lists of search results, removing duplicates.
        
        Args:
            results1: First list of results
            results2: Second list of results
            score_factor: Factor to apply to second list scores (0.9 means 10% penalty)
            
        Returns:
            List[SearchResult]: Merged results
        """
        # Create a map of document IDs to their best result
        result_map = {}
        
        # Add first list of results
        for result in results1:
            result_map[result.id] = result
        
        # Add/update with second list of results (with a score penalty)
        for result in results2:
            # Apply a small penalty to the second list's scores
            adjusted_result = SearchResult(
                id=result.id,
                text=result.text,
                score=result.score * score_factor,  # Apply score penalty
                metadata=result.metadata.copy()
            )
            
            # Keep the result with the highest score
            if result.id not in result_map or adjusted_result.score > result_map[result.id].score:
                result_map[result.id] = adjusted_result
        
        # Convert map back to list and sort by score
        merged_results = list(result_map.values())
        merged_results.sort(key=lambda x: x.score, reverse=True)
        
        return merged_results


# Create a singleton instance
_multilingual_retriever = None

def get_multilingual_retriever() -> MultilingualRetriever:
    """Get the multilingual retriever singleton instance."""
    global _multilingual_retriever
    if _multilingual_retriever is None:
        _multilingual_retriever = MultilingualRetriever(
            translator_enabled=getattr(settings, "enable_translation", False)
        )
    return _multilingual_retriever