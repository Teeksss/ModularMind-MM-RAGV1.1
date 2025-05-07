from typing import Dict, Any, List, Optional, Tuple
import logging
import json
import asyncio
import time
from datetime import datetime
import sqlalchemy
from sqlalchemy import create_engine, text, MetaData, Table, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from pydantic import BaseModel, Field
import pandas as pd

from app.core.settings import get_settings
from app.db.session import get_db

settings = get_settings()
logger = logging.getLogger(__name__)


class SQLSourceConfig(BaseModel):
    """Configuration for a SQL data source."""
    name: str
    connection_string: str
    description: Optional[str] = None
    query: Optional[str] = None
    tables: Optional[List[str]] = None
    schema: Optional[str] = None
    max_rows: int = 1000
    owner_id: str
    id: Optional[str] = None
    created_at: Optional[datetime] = None


class TableSchema(BaseModel):
    """Schema information for a database table."""
    table_name: str
    columns: List[Dict[str, Any]]
    primary_keys: List[str]
    foreign_keys: List[Dict[str, Any]]
    row_count: Optional[int] = None


class SQLSourceService:
    """
    Service for managing SQL data sources.
    
    Handles connection, querying, and schema inspection for SQL databases.
    """
    
    def __init__(self):
        """Initialize the SQL source service."""
        self._engines: Dict[str, Engine] = {}
    
    async def test_connection(self, connection_string: str) -> Tuple[bool, Optional[str]]:
        """
        Test a database connection.
        
        Args:
            connection_string: The SQL connection string
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Create engine
            engine = create_engine(connection_string)
            
            # Test connection
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            return True, None
        
        except SQLAlchemyError as e:
            logger.error(f"SQL connection error: {str(e)}")
            return False, str(e)
        
        except Exception as e:
            logger.error(f"Unexpected error testing connection: {str(e)}")
            return False, str(e)
    
    def _get_engine(self, source_id: str, connection_string: str) -> Engine:
        """Get or create an SQLAlchemy engine for the given source."""
        if source_id not in self._engines:
            self._engines[source_id] = create_engine(connection_string)
        return self._engines[source_id]
    
    async def create_source(self, config: SQLSourceConfig) -> Dict[str, Any]:
        """
        Create a new SQL data source.
        
        Args:
            config: The SQL source configuration
            
        Returns:
            The created source data
        """
        # First test the connection
        success, error = await self.test_connection(config.connection_string)
        if not success:
            raise ValueError(f"Failed to connect to database: {error}")
        
        # Generate ID if not provided
        if not config.id:
            from uuid import uuid4
            config.id = str(uuid4())
        
        # Set creation timestamp
        config.created_at = datetime.now()
        
        # Store in database
        async with get_db() as db:
            query = """
            INSERT INTO datasources (
                id, name, type, config, owner_id, created_at
            ) VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id, name, type, config, owner_id, created_at
            """
            values = (
                config.id,
                config.name,
                "sql",
                json.dumps(config.dict()),
                config.owner_id,
                config.created_at
            )
            
            result = await db.fetch_one(query, *values)
            
            source_data = dict(result)
            source_data["config"] = json.loads(source_data["config"])
            
            return source_data
    
    async def get_source(self, source_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a SQL data source by ID.
        
        Args:
            source_id: The source ID
            
        Returns:
            The source data or None if not found
        """
        async with get_db() as db:
            query = """
            SELECT id, name, type, config, owner_id, created_at
            FROM datasources
            WHERE id = $1 AND type = 'sql'
            """
            
            result = await db.fetch_one(query, source_id)
            
            if not result:
                return None
            
            source_data = dict(result)
            source_data["config"] = json.loads(source_data["config"])
            
            return source_data
    
    async def list_sources(self, owner_id: str) -> List[Dict[str, Any]]:
        """
        List all SQL data sources for an owner.
        
        Args:
            owner_id: The owner ID
            
        Returns:
            List of source data
        """
        async with get_db() as db:
            query = """
            SELECT id, name, type, config, owner_id, created_at
            FROM datasources
            WHERE owner_id = $1 AND type = 'sql'
            ORDER BY created_at DESC
            """
            
            results = await db.fetch_all(query, owner_id)
            
            sources = []
            for row in results:
                source_data = dict(row)
                source_data["config"] = json.loads(source_data["config"])
                sources.append(source_data)
            
            return sources
    
    async def delete_source(self, source_id: str, owner_id: str) -> bool:
        """
        Delete a SQL data source.
        
        Args:
            source_id: The source ID
            owner_id: The owner ID (for authorization)
            
        Returns:
            True if deleted, False otherwise
        """
        async with get_db() as db:
            query = """
            DELETE FROM datasources
            WHERE id = $1 AND owner_id = $2 AND type = 'sql'
            RETURNING id
            """
            
            result = await db.fetch_one(query, source_id, owner_id)
            
            # Close engine if it exists
            if source_id in self._engines:
                self._engines[source_id].dispose()
                del self._engines[source_id]
            
            return result is not None
    
    async def list_tables(self, source_id: str) -> List[str]:
        """
        List all tables in a SQL data source.
        
        Args:
            source_id: The source ID
            
        Returns:
            List of table names
        """
        source = await self.get_source(source_id)
        if not source:
            raise ValueError(f"Source {source_id} not found")
        
        config = SQLSourceConfig(**source["config"])
        engine = self._get_engine(source_id, config.connection_string)
        
        inspector = inspect(engine)
        
        # Get schema if specified, otherwise use default
        schema = config.schema
        
        return inspector.get_table_names(schema=schema)
    
    async def get_table_schema(self, source_id: str, table_name: str) -> TableSchema:
        """
        Get schema information for a table.
        
        Args:
            source_id: The source ID
            table_name: The table name
            
        Returns:
            Table schema information
        """
        source = await self.get_source(source_id)
        if not source:
            raise ValueError(f"Source {source_id} not found")
        
        config = SQLSourceConfig(**source["config"])
        engine = self._get_engine(source_id, config.connection_string)
        
        inspector = inspect(engine)
        
        # Get schema if specified, otherwise use default
        schema = config.schema
        
        # Get column information
        columns = []
        for column in inspector.get_columns(table_name, schema=schema):
            columns.append({
                "name": column["name"],
                "type": str(column["type"]),
                "nullable": column.get("nullable", True),
                "default": str(column.get("default", ""))
            })
        
        # Get primary key information
        pk_constraint = inspector.get_pk_constraint(table_name, schema=schema)
        primary_keys = pk_constraint.get("constrained_columns", [])
        
        # Get foreign key information
        foreign_keys = []
        for fk in inspector.get_foreign_keys(table_name, schema=schema):
            foreign_keys.append({
                "name": fk.get("name", ""),
                "referred_schema": fk.get("referred_schema"),
                "referred_table": fk.get("referred_table"),
                "referred_columns": fk.get("referred_columns", []),
                "constrained_columns": fk.get("constrained_columns", [])
            })
        
        # Get approximate row count
        row_count = None
        try:
            with engine.connect() as conn:
                # Use fast approximation if available, otherwise count
                if engine.dialect.name == 'postgresql':
                    query = text(f"""
                    SELECT reltuples::bigint AS count
                    FROM pg_class
                    WHERE relname = '{table_name}'
                    """)
                    result = conn.execute(query).fetchone()
                    if result:
                        row_count = result[0]
                else:
                    # For other databases, use count but limit runtime
                    query = text(f"SELECT COUNT(*) FROM {table_name}")
                    result = conn.execute(query).fetchone()
                    if result:
                        row_count = result[0]
        except SQLAlchemyError as e:
            logger.warning(f"Could not get row count for {table_name}: {str(e)}")
        
        return TableSchema(
            table_name=table_name,
            columns=columns,
            primary_keys=primary_keys,
            foreign_keys=foreign_keys,
            row_count=row_count
        )
    
    async def execute_query(
        self, 
        source_id: str, 
        query: str,
        max_rows: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute a SQL query and return the results.
        
        Args:
            source_id: The source ID
            query: The SQL query to execute
            max_rows: Maximum number of rows to return
            
        Returns:
            Query results with metadata
        """
        source = await self.get_source(source_id)
        if not source:
            raise ValueError(f"Source {source_id} not found")
        
        config = SQLSourceConfig(**source["config"])
        
        # Use provided max_rows or fall back to config
        max_rows = max_rows or config.max_rows
        
        # Ensure reasonable limit
        max_rows = min(max_rows, 10000)
        
        engine = self._get_engine(source_id, config.connection_string)
        
        start_time = time.time()
        
        try:
            # Execute the query and convert to DataFrame
            with engine.connect() as conn:
                df = pd.read_sql(text(query), conn, params={})
            
            # Apply row limit
            if len(df) > max_rows:
                df = df.head(max_rows)
            
            # Convert to list of dicts for JSON serialization
            rows = df.to_dict(orient='records')
            
            # Get column names and types
            columns = [
                {
                    "name": col,
                    "type": str(df[col].dtype)
                }
                for col in df.columns
            ]
            
            execution_time = time.time() - start_time
            
            return {
                "success": True,
                "rows": rows,
                "columns": columns,
                "row_count": len(rows),
                "execution_time": execution_time,
                "truncated": len(df) >= max_rows,
                "max_rows": max_rows
            }
            
        except SQLAlchemyError as e:
            logger.error(f"SQL execution error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "execution_time": time.time() - start_time
            }
        
        except Exception as e:
            logger.error(f"Unexpected error executing query: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "execution_time": time.time() - start_time
            }
    
    async def extract_content(
        self, 
        source_id: str, 
        tables: Optional[List[str]] = None,
        query: Optional[str] = None,
        max_rows_per_table: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Extract content from SQL source for indexing.
        
        Args:
            source_id: The source ID
            tables: List of tables to extract from (if query not provided)
            query: Custom extraction query (takes precedence over tables)
            max_rows_per_table: Maximum rows to extract per table
            
        Returns:
            List of extracted documents
        """
        source = await self.get_source(source_id)
        if not source:
            raise ValueError(f"Source {source_id} not found")
        
        config = SQLSourceConfig(**source["config"])
        
        # Use provided parameters or fall back to config
        query = query or config.query
        tables = tables or config.tables
        
        # If query is provided, use it for extraction
        if query:
            result = await self.execute_query(source_id, query, max_rows=max_rows_per_table)
            
            if not result["success"]:
                raise ValueError(f"Query execution failed: {result.get('error')}")
            
            # Convert rows to documents
            documents = []
            for i, row in enumerate(result["rows"]):
                # Convert row to a formatted string
                content = "\n".join([f"{k}: {v}" for k, v in row.items()])
                
                documents.append({
                    "id": f"{source_id}_{i}",
                    "content": content,
                    "metadata": {
                        "source_id": source_id,
                        "source_type": "sql",
                        "query": query,
                        "row_index": i
                    }
                })
            
            return documents
        
        # If tables are provided, extract from each table
        elif tables:
            documents = []
            
            engine = self._get_engine(source_id, config.connection_string)
            
            for table in tables:
                try:
                    # Get table schema
                    table_schema = await self.get_table_schema(source_id, table)
                    
                    # Build a simple select query
                    columns_str = ", ".join([f'"{col["name"]}"' for col in table_schema.columns])
                    select_query = f'SELECT {columns_str} FROM "{table}" LIMIT {max_rows_per_table}'
                    
                    # Execute query
                    result = await self.execute_query(source_id, select_query)
                    
                    if not result["success"]:
                        logger.warning(f"Failed to extract from table {table}: {result.get('error')}")
                        continue
                    
                    # Convert rows to documents
                    for i, row in enumerate(result["rows"]):
                        # Convert row to a formatted string
                        content = f"Table: {table}\n"
                        content += "\n".join([f"{k}: {v}" for k, v in row.items()])
                        
                        documents.append({
                            "id": f"{source_id}_{table}_{i}",
                            "content": content,
                            "metadata": {
                                "source_id": source_id,
                                "source_type": "sql",
                                "table": table,
                                "row_index": i
                            }
                        })
                
                except Exception as e:
                    logger.error(f"Error extracting from table {table}: {str(e)}")
            
            return documents
        
        # If neither query nor tables provided
        else:
            # Get all tables and extract from each
            all_tables = await self.list_tables(source_id)
            return await self.extract_content(
                source_id=source_id,
                tables=all_tables,
                max_rows_per_table=max_rows_per_table
            )


# Create a singleton instance
_sql_source_service = SQLSourceService()

def get_sql_source_service() -> SQLSourceService:
    """Get the SQL source service singleton."""
    return _sql_source_service