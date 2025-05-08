"""
Özel ajan çalıştırıcısı.
"""

import logging
import importlib
from typing import Dict, Any

logger = logging.getLogger(__name__)

def run_custom_agent(config, result):
    """
    Özel ajanı çalıştırır.
    
    Args:
        config: Ajan yapılandırması
        result: Sonuç nesnesi
    """
    # Özel modül bilgilerini al
    module_name = config.options.get("module")
    class_name = config.options.get("class")
    
    if not module_name or not class_name:
        raise ValueError("Özel ajan için module ve class seçenekleri gereklidir")
    
    try:
        # Dinamik modül yükleme
        module = importlib.import_module(module_name)
        agent_class = getattr(module, class_name)
        
        # Ajanı oluştur
        agent = agent_class(config)
        
        # Ajanı çalıştır
        agent_result = agent.run()
        
        # Sonuçları dönüştür
        result.documents = agent_result.get("documents", [])
        result.metadata = agent_result.get("metadata", {})
        
    except (ImportError, AttributeError) as e:
        raise ImportError(f"Özel ajan modülü yüklenemedi: {str(e)}")