"""
Veritabanı bağlantı ajan çalıştırıcısı.
"""

import logging
import uuid
import time
from typing import Dict, Any

from ModularMind.API.services.retrieval.models import Document

logger = logging.getLogger(__name__)

def run_database_connector(config, result):
    """
    Veritabanı bağlantı ajanını çalıştırır.
    
    Args:
        config: Ajan yapılandırması
        result: Sonuç nesnesi
    """
    # Veritabanı tipini kontrol et
    db_type = config.options.get("db_type", "")
    
    if db_type == "postgres":
        _run_postgres_connector(config, result)
    elif db_type == "mysql":
        _run_mysql_connector(config, result)
    elif db_type == "sqlite":
        _run_sqlite_connector(config, result)
    else:
        raise ValueError(f"Desteklenmeyen veritabanı tipi: {db_type}")

def _run_postgres_connector(config, result):
    """PostgreSQL bağlantı ajanını çalıştırır."""
    import psycopg2
    import psycopg2.extras
    
    # Bağlantı bilgileri
    connection_string = config.options.get("connection_string", "")
    host = config.options.get("host", "localhost")
    port = config.options.get("port", 5432)
    dbname = config.options.get("database", "")
    user = config.credentials.get("username", "")
    password = config.credentials.get("password", "")
    query = config.options.get("query", "")
    
    if not query:
        raise ValueError("Veritabanı sorgusu gereklidir")
    
    # Bağlan
    if connection_string:
        conn = psycopg2.connect(connection_string)
    else:
        conn = psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password
        )
    
    # Dict cursor kullan
    conn.cursor_factory = psycopg2.extras.RealDictCursor
    
    try:
        with conn.cursor() as cursor:
            # Sorguyu çalıştır
            cursor.execute(query)
            
            # Sonuçları al
            rows = cursor.fetchall()
            
            # Belgeleri oluştur
            documents = []
            
            for row in rows:
                # Metin dönüşümü
                text = _format_row_as_text(row)
                
                # Belge oluştur
                doc_id = f"db_{uuid.uuid4().hex}"
                metadata = {
                    "source": f"postgres:{dbname}",
                    "source_type": "database",
                    "db_type": "postgres",
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                
                # Özel metadata alanlarını ekle
                for key, value in row.items():
                    if key in config.metadata_mapping:
                        metadata[config.metadata_mapping[key]] = str(value)
                
                document = Document(
                    id=doc_id,
                    text=text,
                    metadata=metadata
                )
                
                documents.append(document)
            
            # Sonucu güncelle
            result.documents = documents
            result.metadata["row_count"] = len(rows)
    
    finally:
        conn.close()

def _run_mysql_connector(config, result):
    """MySQL bağlantı ajanını çalıştırır."""
    # Bu implementasyon gerçek uygulamada tamamlanmalıdır
    pass

def _run_sqlite_connector(config, result):
    """SQLite bağlantı ajanını çalıştırır."""
    # Bu implementasyon gerçek uygulamada tamamlanmalıdır
    pass

def _format_row_as_text(row):
    """Veritabanı satırını metin olarak formatlar."""
    text = ""
    for key, value in row.items():
        text += f"{key}: {value}\n"
    return text.strip()