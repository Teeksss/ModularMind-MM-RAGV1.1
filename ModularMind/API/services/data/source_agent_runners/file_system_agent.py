"""
Dosya sistemi ajan çalıştırıcısı.
"""

import logging
import os
import uuid
import time
from typing import Dict, Any

from ModularMind.API.services.retrieval.models import Document

logger = logging.getLogger(__name__)

def run_file_system(config, result):
    """
    Dosya sistemi ajanını çalıştırır.
    
    Args:
        config: Ajan yapılandırması
        result: Sonuç nesnesi
    """
    # Klasör yolunu kontrol et
    folder_path = config.source_url
    if not folder_path or not os.path.isdir(folder_path):
        raise ValueError(f"Geçerli bir klasör yolu değil: {folder_path}")
    
    # Dosya uzantılarını al
    extensions = config.options.get("extensions", [".txt", ".md", ".pdf", ".docx"])
    
    # Son değişiklik zamanını kontrol et
    check_mtime = config.options.get("check_mtime", True)
    
    # Dokümanlar
    documents = []
    
    # Dosyaları tara
    for root, _, files in os.walk(folder_path):
        for file in files:
            # Uzantıyı kontrol et
            _, ext = os.path.splitext(file)
            if ext.lower() not in extensions:
                continue
            
            # Tam dosya yolu
            file_path = os.path.join(root, file)
            
            # Değişiklik zamanını kontrol et
            if check_mtime and config.last_run:
                mtime = os.path.getmtime(file_path)
                if mtime <= config.last_run:
                    continue
            
            # Belge metni burada yüklenmeli
            # Gerçek bir uygulamada dosya tipine göre uygun parser kullanılmalı
            
            # Basit metin örneği
            if ext.lower() in [".txt", ".md"]:
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()
                    
                # Metadata
                metadata = {
                    "source": file_path,
                    "title": os.path.basename(file),
                    "source_type": "file",
                    "file_type": ext.lstrip("."),
                    "modified_time": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(os.path.getmtime(file_path)))
                }
                
                # Belge oluştur
                doc_id = f"file_{uuid.uuid4().hex}"
                document = Document(
                    id=doc_id,
                    text=text,
                    metadata=metadata
                )
                
                # Belgeyi listeye ekle
                documents.append(document)
    
    # Sonucu güncelle
    result.documents = documents