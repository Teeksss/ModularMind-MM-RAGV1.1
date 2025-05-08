"""
LLM Yapılandırma yükleyici.
"""

import os
import json
import logging
from typing import Dict

from ModularMind.API.services.llm.models import LLMProvider, PromptTemplate, LLMModelConfig, PromptConfig

logger = logging.getLogger(__name__)

def load_model_configs() -> Dict[str, LLMModelConfig]:
    """
    Model yapılandırmalarını yükler.
    
    Returns:
        Dict[str, LLMModelConfig]: Model yapılandırmaları
    """
    configs = {}
    
    # Temel yapılandırmalar
    configs["gpt-3.5-turbo"] = LLMModelConfig(
        model_id="gpt-3.5-turbo",
        provider=LLMProvider.OPENAI,
        api_key_env="OPENAI_API_KEY",
        max_tokens=1024,
        temperature=0.7,
        top_p=1.0,
        context_window=16385,
        streaming=True
    )
    
    configs["gpt-4-turbo"] = LLMModelConfig(
        model_id="gpt-4-turbo",
        provider=LLMProvider.OPENAI,
        api_key_env="OPENAI_API_KEY",
        max_tokens=4096,
        temperature=0.7,
        top_p=1.0,
        context_window=128000,
        streaming=True
    )
    
    configs["claude-3-sonnet"] = LLMModelConfig(
        model_id="claude-3-sonnet-20240229",
        provider=LLMProvider.ANTHROPIC,
        api_key_env="ANTHROPIC_API_KEY",
        max_tokens=4096,
        temperature=0.7,
        top_p=1.0,
        context_window=200000,
        streaming=True
    )
    
    # Özel yapılandırmaları yükle
    try:
        models_path = os.path.join(os.path.dirname(__file__), "llm_models_config.json")
        if os.path.exists(models_path):
            with open(models_path, "r") as f:
                custom_models = json.load(f)
            
            for model_id, config in custom_models.items():
                # Enum değerlerini dönüştür
                provider = LLMProvider(config.get("provider", "custom"))
                
                configs[model_id] = LLMModelConfig(
                    model_id=model_id,
                    provider=provider,
                    api_key_env=config.get("api_key_env", ""),
                    base_url=config.get("base_url"),
                    timeout=config.get("timeout", 60),
                    max_tokens=config.get("max_tokens", 1024),
                    temperature=config.get("temperature", 0.7),
                    top_p=config.get("top_p", 1.0),
                    max_retries=config.get("max_retries", 3),
                    retry_interval=config.get("retry_interval", 1),
                    context_window=config.get("context_window", 8192),
                    streaming=config.get("streaming", False),
                    rate_limit_rpm=config.get("rate_limit_rpm"),
                    options=config.get("options")
                )
    except Exception as e:
        logger.error(f"Özel LLM model yapılandırması yükleme hatası: {str(e)}")
    
    return configs

def load_prompt_templates() -> Dict[str, PromptConfig]:
    """
    Prompt şablonlarını yükler.
    
    Returns:
        Dict[str, PromptConfig]: Prompt şablonları
    """
    templates = {}
    
    # Temel şablonlar
    templates["summarize"] = PromptConfig(
        template_id="summarize",
        template_type=PromptTemplate.SUMMARIZE,
        text="Aşağıdaki metni özetle:\n\n{text}\n\nÖzet:",
        variables=["text"],
        required_variables=["text"],
        description="Verilen metni özetler"
    )
    
    templates["extract_info"] = PromptConfig(
        template_id="extract_info",
        template_type=PromptTemplate.EXTRACT_INFO,
        text="Aşağıdaki metinden {info_type} bilgisini çıkar:\n\n{text}\n\n{format_instructions}",
        variables=["text", "info_type", "format_instructions"],
        required_variables=["text", "info_type"],
        description="Metinden belirli bilgileri çıkarır"
    )
    
    templates["analyze"] = PromptConfig(
        template_id="analyze",
        template_type=PromptTemplate.ANALYZE,
        text="Aşağıdaki metni analiz et:\n\n{text}\n\nAnaliz kriteri: {criteria}\n\nAnaliz:",
        variables=["text", "criteria"],
        required_variables=["text"],
        description="Metni belirli kriterlere göre analiz eder"
    )
    
    templates["question_answer"] = PromptConfig(
        template_id="question_answer",
        template_type=PromptTemplate.QUESTION_ANSWER,
        text="Aşağıdaki bağlamı kullanarak soruyu cevapla:\n\nBağlam:\n{context}\n\nSoru: {question}\n\nCevap:",
        variables=["context", "question"],
        required_variables=["context", "question"],
        description="Verilen bağlam üzerinde soru cevaplar"
    )
    
    # Özel şablonları yükle
    try:
        templates_path = os.path.join(os.path.dirname(__file__), "prompt_templates.json")
        if os.path.exists(templates_path):
            with open(templates_path, "r") as f:
                custom_templates = json.load(f)
            
            for template_id, config in custom_templates.items():
                # Enum değerlerini dönüştür
                template_type = PromptTemplate(config.get("template_type", "custom"))
                
                templates[template_id] = PromptConfig(
                    template_id=template_id,
                    template_type=template_type,
                    text=config.get("text", ""),
                    variables=config.get("variables", []),
                    required_variables=config.get("required_variables", []),
                    description=config.get("description", ""),
                    model_specific=config.get("model_specific", {})
                )
    except Exception as e:
        logger.error(f"Özel prompt şablonu yükleme hatası: {str(e)}")
    
    return templates