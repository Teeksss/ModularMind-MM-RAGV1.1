"""
Data connectors for various data sources.

This module provides a unified interface for connecting to various data sources,
including databases, files, APIs, and web resources.
"""

# Base connector classes
from .base import BaseConnector, ConnectorConfig, ConnectorError

# Database connectors
from .database import (
    SQLConnector,
    PostgreSQLConnector,
    MySQLConnector,
    MongoDBConnector,
    ElasticsearchConnector,
    PineconeConnector,
    QdrantConnector,
    WeaviateConnector
)

# File connectors
from .file.local import LocalFileConnector, LocalDirectoryConnector
from .file.cloud import S3Connector, GCSConnector, AzureBlobConnector

# API connectors
from .api.rest import RESTConnector, OpenAPIConnector
from .api.graphql import GraphQLConnector

# Web connectors
from .web.scraper import WebScraperConnector
from .web.crawler import WebCrawlerConnector

# Registry of all available connectors
CONNECTOR_REGISTRY = {
    # Database connectors
    "postgresql": PostgreSQLConnector,
    "mysql": MySQLConnector,
    "mongodb": MongoDBConnector,
    "elasticsearch": ElasticsearchConnector,
    "pinecone": PineconeConnector,
    "qdrant": QdrantConnector,
    "weaviate": WeaviateConnector,
    
    # File connectors
    "local_file": LocalFileConnector,
    "local_dir": LocalDirectoryConnector,
    "s3": S3Connector,
    "gcs": GCSConnector,
    "azure_blob": AzureBlobConnector,
    
    # API connectors
    "rest": RESTConnector,
    "openapi": OpenAPIConnector,
    "graphql": GraphQLConnector,
    
    # Web connectors
    "web_scraper": WebScraperConnector,
    "web_crawler": WebCrawlerConnector
}

def get_connector(connector_type, config):
    """
    Connector factory method
    
    Args:
        connector_type (str): Type of connector to create
        config (dict): Configuration for the connector
        
    Returns:
        BaseConnector: An instance of the requested connector
        
    Raises:
        ValueError: If connector_type is not supported
    """
    if connector_type not in CONNECTOR_REGISTRY:
        raise ValueError(f"Unsupported connector type: {connector_type}")
    
    return CONNECTOR_REGISTRY[connector_type](config)

__all__ = [
    'BaseConnector',
    'ConnectorConfig',
    'ConnectorError',
    'get_connector',
    'CONNECTOR_REGISTRY',
    # All connector classes
    'SQLConnector',
    'PostgreSQLConnector',
    'MySQLConnector',
    'MongoDBConnector',
    'ElasticsearchConnector',
    'PineconeConnector',
    'QdrantConnector',
    'WeaviateConnector',
    'LocalFileConnector',
    'LocalDirectoryConnector',
    'S3Connector',
    'GCSConnector',
    'AzureBlobConnector',
    'RESTConnector',
    'OpenAPIConnector',
    'GraphQLConnector',
    'WebScraperConnector',
    'WebCrawlerConnector'
]