"""
Base connector classes for all data connectors.
"""
from typing import Dict, Any, Optional, List, Union
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class ConnectorError(Exception):
    """Base exception class for connector errors"""
    pass

class ConnectorConfig:
    """Configuration class for connectors"""
    
    def __init__(self, config_dict: Dict[str, Any]):
        """
        Initialize connector configuration from dictionary
        
        Args:
            config_dict: Configuration dictionary
        """
        self.config = config_dict
        
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self.config.get(key, default)
    
    def __getitem__(self, key: str) -> Any:
        """Dictionary-like access to configuration"""
        return self.config[key]
    
    def __contains__(self, key: str) -> bool:
        """Check if configuration contains key"""
        return key in self.config
    
    @property
    def credentials(self) -> Dict[str, Any]:
        """Get credentials section of configuration"""
        return self.config.get('credentials', {})
    
    @property
    def options(self) -> Dict[str, Any]:
        """Get options section of configuration"""
        return self.config.get('options', {})

class BaseConnector(ABC):
    """Base connector class that all data connectors should inherit from"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize connector with configuration
        
        Args:
            config: Connector configuration dictionary
        """
        self.config = ConnectorConfig(config)
        self.connection = None
        self.is_connected = False
        
    @abstractmethod
    def connect(self) -> bool:
        """
        Establish connection to the data source
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """
        Close connection to the data source
        
        Returns:
            bool: True if disconnect successful, False otherwise
        """
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """
        Test if connection works
        
        Returns:
            bool: True if connection works, False otherwise
        """
        pass
    
    @abstractmethod
    def fetch_data(self, query: Any) -> List[Dict[str, Any]]:
        """
        Fetch data from the source
        
        Args:
            query: Query to fetch data
            
        Returns:
            List[Dict[str, Any]]: List of records
        """
        pass
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()