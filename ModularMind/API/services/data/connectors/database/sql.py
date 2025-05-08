"""
SQL database connectors for ModularMind
"""
import logging
from typing import Dict, Any, List, Optional, Tuple, Union
import time

from ..base import BaseConnector, ConnectorError

logger = logging.getLogger(__name__)

class SQLConnector(BaseConnector):
    """Base class for SQL database connectors"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize SQL connector with configuration"""
        super().__init__(config)
        self.connection = None
        self.cursor = None
    
    def connect(self) -> bool:
        """Establish connection to SQL database"""
        # This is abstract in the base class, subclasses will implement specific logic
        raise NotImplementedError("Subclasses must implement connect() method")
    
    def disconnect(self) -> bool:
        """Close connection to SQL database"""
        if self.connection:
            try:
                if self.cursor:
                    self.cursor.close()
                self.connection.close()
                self.is_connected = False
                return True
            except Exception as e:
                logger.error(f"Error disconnecting from SQL database: {e}")
                return False
        return True
    
    def test_connection(self) -> bool:
        """Test SQL database connection"""
        try:
            if not self.is_connected:
                self.connect()
            
            # Simple test query
            self.execute_query("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
        
    def execute_query(self, query: str, params: Optional[Union[Tuple, Dict]] = None) -> Any:
        """
        Execute SQL query
        
        Args:
            query: SQL query string
            params: Query parameters (optional)
            
        Returns:
            Query result
        """
        if not self.is_connected:
            self.connect()
            
        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)
                
            return self.cursor
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            raise ConnectorError(f"Query execution failed: {str(e)}")
    
    def fetch_data(self, query: str, params: Optional[Union[Tuple, Dict]] = None) -> List[Dict[str, Any]]:
        """
        Fetch data from SQL database
        
        Args:
            query: SQL query
            params: Query parameters (optional)
            
        Returns:
            List of records as dictionaries
        """
        cursor = self.execute_query(query, params)
        
        if cursor.description is None:
            return []
            
        columns = [col[0] for col in cursor.description]
        result = []
        
        for row in cursor.fetchall():
            result.append(dict(zip(columns, row)))
            
        return result

class PostgreSQLConnector(SQLConnector):
    """PostgreSQL database connector"""
    
    def connect(self) -> bool:
        """Connect to PostgreSQL database"""
        try:
            import psycopg2
            import psycopg2.extras
            
            # Get connection parameters
            host = self.config.get('host', 'localhost')
            port = self.config.get('port', 5432)
            database = self.config.get('database')
            user = self.config.get('user')
            password = self.config.get('password')
            
            if not database:
                raise ConnectorError("Database name is required")
                
            # Establish connection
            self.connection = psycopg2.connect(
                host=host,
                port=port,
                dbname=database,
                user=user,
                password=password
            )
            
            # Use DictCursor for dictionary-like access
            self.cursor = self.connection.cursor(cursor_factory=psycopg2.extras.DictCursor)
            self.is_connected = True
            return True
            
        except ImportError:
            logger.error("psycopg2 module not found. Install with: pip install psycopg2-binary")
            raise ConnectorError("psycopg2 module not found")
        except Exception as e:
            logger.error(f"Error connecting to PostgreSQL: {e}")
            raise ConnectorError(f"PostgreSQL connection failed: {str(e)}")

class MySQLConnector(SQLConnector):
    """MySQL database connector"""
    
    def connect(self) -> bool:
        """Connect to MySQL database"""
        try:
            import mysql.connector
            
            # Get connection parameters
            host = self.config.get('host', 'localhost')
            port = self.config.get('port', 3306)
            database = self.config.get('database')
            user = self.config.get('user')
            password = self.config.get('password')
            
            if not database:
                raise ConnectorError("Database name is required")
                
            # Establish connection
            self.connection = mysql.connector.connect(
                host=host,
                port=port,
                database=database,
                user=user,
                password=password
            )
            
            self.cursor = self.connection.cursor(dictionary=True)
            self.is_connected = True
            return True
            
        except ImportError:
            logger.error("mysql.connector module not found. Install with: pip install mysql-connector-python")
            raise ConnectorError("mysql.connector module not found")
        except Exception as e:
            logger.error(f"Error connecting to MySQL: {e}")
            raise ConnectorError(f"MySQL connection failed: {str(e)}")