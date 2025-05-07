from typing import Dict, List, Optional, Union, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.services.language_detection import get_language_detector, get_text_preprocessor
from app.api.deps import get_current_user, get_current_admin_user
from app.models.user import User
from app.services.translation import get_translation_service

router = APIRouter()


class DetectLanguageRequest(BaseModel):
    """Request for language detection."""
    text: str


class DetectLanguageResponse(BaseModel):
    """Response for language detection."""
    language: str
    language_name: str
    confidence: Optional[float] = None


class PreprocessTextRequest(BaseModel):
    """Request for text preprocessing."""
    text: str
    language: Optional[str] = None
    remove_stopwords: bool = False
    normalize_chars: bool = True
    stem: bool = False


class PreprocessTextResponse(BaseModel):
    """Response for text preprocessing."""
    processed_text: str
    language: str
    language_name: str


class TranslateTextRequest(BaseModel):
    """Request for text translation."""
    text: str
    source_language: Optional[str] = None
    target_language: str = "en"
    force_refresh: bool = False


class TranslateTextResponse(BaseModel):
    """Response for text translation."""
    translated_text: str
    source_language: str
    target_language: str
    execution_time: Optional[float] = None


@router.post(
    "/detect",
    response_model=DetectLanguageResponse,
    summary="Detect the language of text"
)
async def detect_language(
    request: DetectLanguageRequest,
    current_user: User = Depends(get_current_user)
):
    """Detect the language of provided text."""
    language_detector = get_language_detector()
    
    # Detect language
    language = await language_detector.detect_language(request.text)
    
    # Get language name
    language_name = language_detector.get_language_name(language)
    
    return {
        "language": language,
        "language_name": language_name,
        "confidence": None  # Could add confidence if available in the future
    }


@router.post(
    "/preprocess",
    response_model=PreprocessTextResponse,
    summary="Preprocess text for better retrieval"
)
async def preprocess_text(
    request: PreprocessTextRequest,
    current_user: User = Depends(get_current_user)
):
    """Preprocess text for better retrieval based on language."""
    text_preprocessor = get_text_preprocessor()
    language_detector = get_language_detector()
    
    # Detect language if not provided
    language = request.language
    if not language:
        language = await language_detector.detect_language(request.text)
    
    # Preprocess text
    processed_text = await text_preprocessor.preprocess(
        text=request.text,
        language=language,
        remove_stopwords=request.remove_stopwords,
        normalize_chars=request.normalize_chars,
        stem=request.stem
    )
    
    # Get language name
    language_name = language_detector.get_language_name(language)
    
    return {
        "processed_text": processed_text,
        "language": language,
        "language_name": language_name
    }


@router.post(
    "/translate",
    response_model=TranslateTextResponse,
    summary="Translate text between languages"
)
async def translate_text(
    request: TranslateTextRequest,
    current_user: User = Depends(get_current_user)
):
    """Translate text from source language to target language."""
    translation_service = get_translation_service()
    language_detector = get_language_detector()
    
    # Detect source language if not provided
    source_language = request.source_language
    if not source_language:
        source_language = await language_detector.detect_language(request.text)
    
    # Translate text
    try:
        import time
        start_time = time.time()
        
        translated_text = await translation_service.translate(
            text=request.text,
            source_language=source_language,
            target_language=request.target_language,
            force_refresh=request.force_refresh
        )
        
        execution_time = time.time() - start_time
        
        return {
            "translated_text": translated_text,
            "source_language": source_language,
            "target_language": request.target_language,
            "execution_time": execution_time
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Translation error: {str(e)}"
        )


@router.get(
    "/supported",
    summary="Get supported languages"
)
async def get_supported_languages(
    include_details: bool = False,
    current_user: Optional[User] = Depends(get_current_user)
):
    """Get list of supported languages for the system."""
    language_detector = get_language_detector()
    
    # Get supported languages from language detector
    supported_languages = language_detector.language_names
    
    if include_details:
        # Return detailed information about each language
        return {
            "languages": [
                {
                    "code": code,
                    "name": name,
                    "native_name": name,  # Replace with actual native names in the future
                    "supported_features": ["detection", "retrieval"]
                }
                for code, name in supported_languages.items()
            ],
            "default_language": "en",
            "count": len(supported_languages)
        }
    else:
        # Just return language codes and names
        return {
            "languages": {code: name for code, name in supported_languages.items()},
            "default_language": "en",
            "count": len(supported_languages)
        }