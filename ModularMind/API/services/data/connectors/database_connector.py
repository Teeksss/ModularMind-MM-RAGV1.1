"""
Veritabanı konnektörü.
"""

import logging
from typing import Dict, List, Any, Optional

from ModularMind.API.services.data.connector_models import ConnectorConfig, BaseConnector

logger = logging.getLogger(__name__)

class DatabaseConnector(BaseConnector):
    """Veritabanı konnektörü sınıfı."""
    
    def __init__(self, config: ConnectorConfig):
        super().__init__(config)
        self.connection = None
        self.db_type = config.options.get("db_type", "postgres")
    
    def connect(self) -> bool:
        """Veritabanına bağlanır."""
        try:
            if self.db_type == "postgres":
                return self._connect_postgres()
            elif self.db_type == "mysql":
                return self._connect_mysql()
            elif self.db_type == "sqlite":
                return self._connect_sqlite()
            else:
                logger.error(f"Desteklenmeyen veritabanı tipi: {self.db_type}")
                return False
        except Exception as e:
            logger.error(f"Veritabanı bağlantı hatası: {str(e)}")
            return False
    
    def disconnect(self) -> None:
        """Veritabanı bağlantısını kapatır."""
        if self.connection:
            try:
                self.connection.close()
                self.is_connected = False
                self.connection = None
            except Exception as e:
                logger.error(f"Veritabanı bağlantısı kapatılırken hata: {str(e)}")
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Sorgu çalıştırır."""
        if not self.is_connected:
            if not self.connect():
                raise ValueError("Veritabanına bağlanılamadı")
        
        try:
            if self.db_type == "postgres":
                return self._execute_postgres_query(query, params)
            elif self.db_type == "mysql":
                return self._execute_mysql_query(query, params)
            elif self.db_type == "sqlite":
                return self._execute_sqlite_query(query, params)
            else:
                raise ValueError(f"Desteklenmeyen veritabanı tipi: {self.db_type}")
        except Exception as e:
            logger.error(f"Sorgu çalıştırma hatası: {str(e)}")
            raise
    
    def get_metadata(self) -> Dict[str, Any]:
        """Veritabanı metadata bilgilerini döndürür."""
        if not self.is_connected:
            if not self.connect():
                raise ValueError("Veritabanına bağlanılamadı")
        
        try:
            if self.db_type == "postgres":
                return self._get_postgres_metadata()
            elif self.db_type == "mysql":
                return self._get_mysql_metadata()
            elif self.db_type == "sqlite":
                return self._get_sqlite_metadata()
            else:
                raise ValueError(f"Desteklenmeyen veritabanı tipi: {self.db_type}")
        except Exception as e:
            logger.error(f"Metadata getirme hatası: {str(e)}")
            raise
    
    def _connect_postgres(self) -> bool:
        """PostgreSQL veritabanına bağlanır."""
        try:
            import psycopg2
            import psycopg2.extras
            
            # Bağlantı bilgileri
            connection_string = self.config.connection_string
            host = self.config.options.get("host", "localhost")
            port = self.config.options.get("port", 5432)
            dbname = self.config.options.get("database", "")
            user = self.config.credentials.get("username", "")
            password = self.config.credentials.get("password", "")
            
            # Bağlan
            if connection_string:
                self.connection = psycopg2.connect(connection_string)
            else:
                self.connection = psycopg2.connect(
                    host=host,
                    port=port,
                    dbname=dbname,
                    user=user,
                    password=password
                )
            
            # Dict cursor kullan
            self.connection.cursor_factory = psycopg2.extras.RealDictCursor
            
            self.is_connected = True
            return True
            
        except ImportError:
            logger.error("psycopg2 kütüphanesi bulunamadı")
            return False
        except Exception as e:
            logger.error(f"PostgreSQL bağlantı hatası: {str(e)}")
            return False
    
    def _connect_mysql(self) -> bool:
        """MySQL veritabanına bağlanır."""
        try:
            import mysql.connector
            
            # Bağlantı bilgileri
            connection_string = self.config.connection_string
            host = self.config.options.get("host", "localhost")
            port = self.config.options.get("port", 3306)
            database = self.config.options.get("database", "")
            user = self.config.credentials.get("username", "")
            password = self.config.credentials.get("password", "")
            
            # Bağlan
            if connection_string:
                # Parse connection string
                # Bu kısım gerçek uygulamada implemente edilmelidir
                self.connection = mysql.connector.connect(connection_string)
            else:
                self.connection = mysql.connector.connect(
                    host=host,
                    port=port,
                    database=database,
                    user=user,
                    password=password
                )
            
            self.is_connected = True
            return True
            
        except ImportError:
            logger.error("mysql.connector kütüphanesi bulunamadı")
            return False
        except Exception as e:
            logger.error(f"MySQL bağlantı hatası: {str(e)}")
            return False
    
    def _connect_sqlite(self) -> bool:
        """SQLite veritabanına bağlanır."""
        try:
            import sqlite3
            
            # Bağlantı bilgileri
            database_path = self.config.options.get("database_path", "")
            
            if not database_path:
                logger.error("SQLite için database_path gereklidir")
                return False
            
            # Bağlan
            self.connection = sqlite3.connect(database_path)
            self.connection.row_factory = sqlite3.Row
            
            self.is_connected = True
            return True
            
        except ImportError:
            logger.error("sqlite3 kütüphanesi bulunamadı")
            return False
        except Exception as e:
            logger.error(f"SQLite bağlantı hatası: {str(e)}")
            return False
    
    def _execute_postgres_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """PostgreSQL sorgusu çalıştırır."""
        results = []
        
        with self.connection.cursor() as cursor:
            # Parametreleri kullan veya boş geç
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            # Sonuçları al
            if cursor.description:  # SELECT türü sorgular için
                results = cursor.fetchall()
            
            # Değişiklikleri kaydet, DML işlemleri için
            self.connection.commit()
        
        # Dict formatına dönüştür
        return [dict(row) for row in results]
    
    def _execute_mysql_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """MySQL sorgusu çalıştırır."""
        cursor = self.connection.cursor(dictionary=True)
        
        try:
            # Parametreleri kullan veya boş geç
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            # Sonuçları al
            results = []
            if cursor.description:  # SELECT türü sorgular için
                results = cursor.fetchall()
            
            # Değişiklikleri kaydet, DML işlemleri için
            self.connection.commit()
            
            return results
            
        finally:
            cursor.close()
    
    def _execute_sqlite_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """SQLite sorgusu çalıştırır."""
        cursor = self.connection.cursor()
        
        try:
            # Parametreleri kullan veya boş geç
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            # Sonuçları al
            results = []
            if cursor.description:  # SELECT türü sorgular için
                results = cursor.fetchall()
            
            # Değişiklikleri kaydet, DML işlemleri için
            self.connection.commit()
            
            # Dict formatına dönüştür
            return [dict(row) for row in results]
            
        finally:
            cursor.close()
    
    def _get_postgres_metadata(self) -> Dict[str, Any]:
        """PostgreSQL metadata bilgilerini döndürür."""
        metadata = {
            "tables": [],
            "version": "",
            "database": ""
        }
        
        try:
            # Veritabanı versiyonu
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT version()")
                metadata["version"] = cursor.fetchone()["version"]
            
            # Veritabanı adı
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT current_database()")
                metadata["database"] = cursor.fetchone()["current_database"]
            
            # Tablolar
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    SELECT table_name, table_schema
                    FROM information_schema.tables
                    WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
                    ORDER BY table_schema, table_name
                """)
                metadata["tables"] = [dict(row) for row in cursor.fetchall()]
            
            return metadata
            
        except Exception as e:
            logger.error(f"PostgreSQL metadata hatası: {str(e)}")
            return metadata
    
    def _get_mysql_metadata(self) -> Dict[str, Any]:
        """MySQL metadata bilgilerini döndürür."""
        metadata = {
            "tables": [],
            "version": "",
            "database": ""
        }
        
        cursor = self.connection.cursor(dictionary=True)
        
        try:
            # Veritabanı versiyonu
            cursor.execute("SELECT version() as version")
            version_row = cursor.fetchone()
            if version_row:
                metadata["version"] = version_row["version"]
            
            # Veritabanı adı
            cursor.execute("SELECT database() as db")
            db_row = cursor.fetchone()
            if db_row:
                metadata["database"] = db_row["db"]
            
            # Tablolar
            cursor.execute("""
                SELECT table_name, table_schema
                FROM information_schema.tables
                WHERE table_schema = database()
                ORDER BY table_name
            """)
            metadata["tables"] = cursor.fetchall()
            
            return metadata
            
        except Exception as e:
            logger.error(f"MySQL metadata hatası: {str(e)}")
            return metadata
        finally:
            cursor.close()
    
    def _get_sqlite_metadata(self) -> Dict[str, Any]:
        """SQLite metadata bilgilerini döndürür."""
        metadata = {
            "tables": [],
            "version": "",
            "database": self.config.options.get("database_path", "")
        }
        
        cursor = self.connection.cursor()
        
        try:
            # Veritabanı versiyonu
            cursor.execute("SELECT sqlite_version() as version")
            version_row = cursor.fetchone()
            if version_row:
                metadata["version"] = version_row["version"]
            
            # Tablolar
            cursor.execute("""
                SELECT name as table_name FROM sqlite_master
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """)
            metadata["tables"] = cursor.fetchall()
            
            return metadata
            
        except Exception as e:
            logger.error(f"SQLite metadata hatası: {str(e)}")
            return metadata
        finally:
            cursor.close()